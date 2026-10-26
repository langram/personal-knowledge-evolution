"""Deterministic public-copy redactions. Never modify the source archive."""
import hashlib,re

PATTERNS=[
 ('private-key',r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----'),
 ('github-token',r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
 ('provider-api-key',r'\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{24,}\b'),
 ('google-api-key',r'\bAIza[0-9A-Za-z_-]{30,}\b'),
 ('aws-access-key',r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 ('slack-token',r'\bxox[baprs]-[A-Za-z0-9-]{15,}\b'),
 ('jwt',r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b'),
 ('bearer-token',r'(?i)(?<=Bearer )[A-Za-z0-9_~+/.-]{20,}={0,2}'),
 ('export-download-url',r'https?://(?:claude\.ai|chatgpt\.com|chat\.openai\.com)/[^\s<>"\x27]*(?:export|download)/[^\s<>"\x27]{20,}'),
 ('signed-url',r'https?://[^\s<>"\x27]+[?&](?:sig|signature|X-Amz-Signature|access_token|authkey|token|code)=[^\s<>"\x27]+'),
]
COMPILED=[(name,re.compile(pattern)) for name,pattern in PATTERNS]
ASSIGN=re.compile(r'''(?ix)(["']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|secret[_-]?key|auth[_-]?token)["']?\s*[:=]\s*["'])([^"'\r\n]{6,})(["'])''')
CHINESE=re.compile(r'((?:密码|密钥|令牌)(?:是|为|：|:|=)\s*)([A-Za-z0-9_!@#$%^&*+=.-]{6,})')

def plausible(value):
    if value.startswith('[REDACTED:'):return False
    lowered=value.lower()
    if any(x in lowered for x in ('example','placeholder','your_','your-','your ','dummy','redacted','xxxx','test-token','test_key','test-key','changeme','getenv','environ','process.env','${','{{')):return False
    if value in {'password','api_key','api-key','token','secret','undefined','null','abcdef','123456','12345678'}:return False
    if ' ' in value or '\\' in value:return False
    return True

def sanitize(text):
    findings=[]
    def mark(kind,value):
        findings.append({'kind':kind,'characters':len(value)})
        return '[REDACTED:'+kind+']'
    for kind,pattern in COMPILED:
        def sub(match,kind=kind):
            value=match.group()
            return mark(kind,value) if plausible(value) or kind=='private-key' else value
        text=pattern.sub(sub,text)
    def assignment(match):
        return match[1]+mark('credential-value',match[2])+match[3] if plausible(match[2]) else match[0]
    text=ASSIGN.sub(assignment,text)
    text=CHINESE.sub(lambda m:m[1]+mark('credential-value',m[2]) if plausible(m[2]) else m[0],text)
    return text,findings

def tree(value):
    findings=[]
    if isinstance(value,str):return sanitize(value)
    if isinstance(value,list):
        result=[]
        for item in value:
            clean,found=tree(item);result.append(clean);findings.extend(found)
        return result,findings
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            clean,found=tree(item)
            if isinstance(item,str) and key.lower() in {'password','passwd','access_token','refresh_token','api_key','client_secret','secret_key'} and plausible(item) and not found:
                clean='[REDACTED:credential-value]'
                found=[{'kind':'credential-value','characters':len(item)}]
            result[key]=clean;findings.extend(found)
        return result,findings
    return value,findings
