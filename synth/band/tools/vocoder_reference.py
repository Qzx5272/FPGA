"""Stateful integer filter reference; no HDL or tool side effects."""
def wrap(n): return (n+2**31)%2**32-2**31

class Cascade:
    def __init__(self,c): self.c=c; self.history=[[0]*4 for _ in range(2)]
    def step(self,x):
        for k in range(2):
            b0,b1,b2,a1,a2=self.c[k*5:k*5+5]
            x1,x2,y1,y2=self.history[k]
            y=wrap(b0*x>>20)
            for t in (-(a1*y1>>20),b1*x1>>20,-(a2*y2>>20),b2*x2>>20): y=wrap(y+t)
            self.history[k]=[x,x1,y,y1]; x=y
        return x

