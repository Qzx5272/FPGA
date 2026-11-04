"""Independent TMDS encoder and inverse-check oracle; no HDL dependency."""
control=[0b1101010100,0b0010101011,0b0101010100,0b1010101011]
def encode(value,disparity):
    xnor=value.bit_count()>4 or (value.bit_count()==4 and not value&1)
    bits=[value&1]
    for i in range(1,8):bits.append(bits[-1]^((value>>i)&1)^xnor)
    q=sum(int(bit)<<i for i,bit in enumerate(bits));q8=int(not xnor)
    balance=2*q.bit_count()-8
    if disparity==0 or balance==0:
        invert=1-q8;disparity+=balance if q8 else -balance
    elif (disparity>0 and balance>0) or (disparity<0 and balance<0):
        invert=1;disparity+=2*q8-balance
    else:
        invert=0;disparity+=balance-2*(1-q8)
    word=(invert<<9)|(q8<<8)|(q^(255 if invert else 0))
    # Separately reverse transition coding to prove the original byte survives.
    restored=(word&255)^(255 if word&512 else 0)
    decoded=restored&1
    for i in range(1,8):decoded|=(((restored>>i)^(restored>>(i-1))^(1-q8))&1)<<i
    assert decoded==value
    return word,disparity
