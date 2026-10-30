from composition import assemble
from chapter import compose as chapter
from appendix import compose as appendix

if __name__=='__main__': assemble(chapter(),appendix())
