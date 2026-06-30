import base64
import zlib


ANNEX_C_COLUMNS = ('1A', '1B', '1D', '1E', '1G', '1I', '1K', '1L')

ANNEX_C_COLUMN_TO_MATCH = {
    '1A': 79,
    '1B': 85,
    '1D': 81,
    '1E': 74,
    '1G': 82,
    '1I': 77,
    '1K': 87,
    '1L': 80,
}

ANNEX_C_COMPRESSED = (
    'c-mE1NwzFI3ftGK(M{X9iQNBsD#NJZPjvvxAPB;LpVmjr^>58j`-?vQ_m{~2*XF1H#n?m+kwfGm@(}p~`7+Mh|JJyX8E2h;>-'
    '^`e_0WcK*7x6vAJP?P|4u*u;j@3Ij~ChW+Fu}F+MI`8v^ifOiu}k6HuL5DW~1}0`EpL=5P68m>kEXD=a2Ka$fnniGZ1?HI445R^U'
    '&td=E#O|9wD$<8(9_SwUJewwSH$M!n4-zEO^o8cUB_2#d_ogoBc98HS&HLo*H?-'
    '40rW9k8BbN<(b+D<vIEx@(_`iG`4_jDs$6oQ<<AyTV6ct(B{zQ$cAwqA+S-'
    'N#rftrN;cx=IZ8G{dDbnKb%<NsJV(vXmU_1kc_H$f=e8@uH_xz1WM0lyhx2l-I-'
    'Hkt)#1FHs}ASYM%CfGoU0C}IL|Evd?q8mocDjc#CZZ)Tgu!*q|6QEJ-updy>V96*nW{+kWo~Zoid8*vb#r7-H;b<in%dD-'
    '3`@^P<NwVBh=lf*9dhtR5wE14b_cMcLzCJb>yt>)>-'
    'Oqon_VW7V2)@Lfx&i)ZL1#?p9=Vx4hKdM5Z`TaK5U$_gY&vxas=RhMec14LMJ6zN&*4Y{YqPA>cC^d8gOkZuAmosBSF9A;YCOWVm'
    '#9p1u@^$OfXb!aWGJgnJNq4)-'
    'AP9PUA=CESBhOSlJvXQ2m!*$DPvFdN|>loxt1n2m4`lA(K$4Bdl_;~pg99t1KS84RZ*gW+6axag(GU^pEa$TE^%UH#6@p{w7y$#n'
    'HQ_k^x~=bq5j@BGSi^*iTtSHE*UclA5JGF|=7uS{3Jb7FV(d*O_JFK40O%US51atriMxdr;YoCVF7$k2R=49yoWDBQ>t=Lyd2_l|'
    'Dr>i3Rr>gxB7e(&n{j(+dz_pX{wah_WU_)JDtzju0x^8~UKhYXkEkm1tZdHPZuBJOvbrGA%M)bGl(`dxWeze_FZcd14FuFPk@N6A'
    'L^dz5Ub-;3AFIZ8Iv?`FuZG(+~g<FG4@um^=qM+U>`$Y7{`S5~JZgW+^!Aj?R4ji3$#IvhbA2C6)QIt)~K1a%nD;Rxz5pu-'
    'W=VfZZQhm&>$b;wCO!a59kK`orLBbMTj;Zhtjqz--hQXC@IA<mkN{I|exGV%|}$eH=eaM6o#78p)P2C|H#SE$O&MySfnM&wz`*$7'
    'pc*$7oxNS?KPuUU|5(=_J?HuI)AfAFW-H0KBQ@TNH*_}^)m^KBl?-'
    'iA5f=0IOG%=tvVw7Gv12eY?f&L^VCkGx=$TCJRO&Ik71ra2$jdz<Eby+vxZ-XiCGVDD|1^X=4I<W^8`asMX9E(~)kD4a3b4*oP7='
    'KRenIb*U7bH-'
    '#l_|t5h^A`bUOtxXp*<aUY3;6<J<W%o2URRlElL(Yq7($taVJdT!I8bKc1I^neoDEcvbKVu?oOcDo*+2zz+CVJ}$RjV<Y-'
    'wx@kryK03QkuLdtKTjf@~Cq$VOq9*@$veWTWuesSTfn2~g^V2~g_A3E;?>0Ht1-'
    '00m*c%WKrkUmcFH4l_R^ti#ODsF@$MA;av`5!PYwEa^~@r9(xQ4&@~s60r^$$2w#j>rh_OArb2k2<H5I*4jdF`pU?h^BcQy<D5^M'
    'L>xKis^+}BqEtC=5v9s`izrnNda24pTxB4o%8AT^Tt3}($9(RtJNlx#?&yo|x??_f*B$e@yYA3)cil^5WVJ*_R*M(1YJ_!n9M;`&'
    'Soh+Ex*K6FgsAS=V7u#%4Ys@P*pa&HZp4w1=Vc^qTzB5Wb>}TycQSO{jj--QRAnNwAeYYw-'
    '4r|02;CGr(g@uY8_@{e)ClhtjJ%Ab%@l(DC(I|kKHN9nx54%5@Z){s)6TnZe7JAGMqXbaU)tdH@;DA&FW>JmkuQ)hZSZ<|92u{d$'
    'B`d-!DitV-JBO*(U;Czctu}2YvE1Lx8UogZ?PVE!G<q^z6D<beTxmREib+VinCr$P6ubbBdxw=^9Ayy4PH)8AGE>C$?4#%ccj&M*'
    '2e4HQRI!+xueL~mfM!sd1RA_-jT#m??_^(cO;#zcO)U)v2~W;k<Pnse7J9<qPA?LG1@R2@4oTzzHx01kVgn?wlubdNMne+;kD&;9'
    '@!+aw)C@wNIx40-'
    'm!K1q7sB`B0P%|$@Stya=rA&p&W7|xn7(|M)ZF{uTe99b?E=fhI{$Hvf*B%W`59y46}FqU)gX|eRp1)Ed&}<Wa&^|(jgJ+ka4U-'
    '#<33NB^?s64uMQZo?8gKW=7V3WxIcfpXUF{wk8lq2C|H#SClH}EuvI8ZxN-+K`&LAh^q{wR5_7ZkjuyW2Iq5k-'
    'J$31x<k+2H#ncYZ*V?$*BuJ?zQK<3zQK<3zQHc=zQK;`uDcoPT}ur0uBFrUt|f%E&{@-'
    'w=N1C5nUPiZo)zq_dtb=vbYvjQNP4;M%!cdEY`E@Z=(;l-uDcLbnO?IXmyh<1-z!AkRQtw7-qXErd?Gn(-'
    '$<K8c&}jOWhA}4Z+z0r`v$xkb@=|r-EViJ4&V2LTjfR_Ci0~X{u%GLyHSUU{B+o;LwLa^C;!OIH|j7EM&9t+@;Z-'
    'f5?Oq65W~ec2QgfHbI|FFZw^8>5uWA$o%@AtW$(=|Y%6<jeotH3dyQn~e>Mk*|94;mC1l375an<K!GAY6LkX}+ByaJvL4Kfw_YWF'
    '2th@M>y*FogD|>Iw@K*NToY<}Gy+(XfAmyfs%z|9iMdkC_^ui~z(F>o<MlXEwUcK-!LOz|5{l@{DS&)}cFMQH#gl%re{U7@XXP^'
)


def _annex_c_table():
    raw = zlib.decompress(base64.b85decode(ANNEX_C_COMPRESSED.encode('ascii'))).decode('ascii')
    return dict(item.split(':', 1) for item in raw.split(';') if item)


ANNEX_C_TABLE = _annex_c_table()


ROUND_OF_32_MATCHUPS = {
    73: (('segundos', 'A', '2° Grupo A'), ('segundos', 'B', '2° Grupo B')),
    74: (('primeros', 'E', '1° Grupo E'), ('terceros', '1E', 'Mejor 3° ABCDF')),
    75: (('primeros', 'F', '1° Grupo F'), ('segundos', 'C', '2° Grupo C')),
    76: (('primeros', 'C', '1° Grupo C'), ('segundos', 'F', '2° Grupo F')),
    77: (('primeros', 'I', '1° Grupo I'), ('terceros', '1I', 'Mejor 3° CDFGH')),
    78: (('segundos', 'E', '2° Grupo E'), ('segundos', 'I', '2° Grupo I')),
    79: (('primeros', 'A', '1° Grupo A'), ('terceros', '1A', 'Mejor 3° CEFHI')),
    80: (('primeros', 'L', '1° Grupo L'), ('terceros', '1L', 'Mejor 3° EHIJK')),
    81: (('primeros', 'D', '1° Grupo D'), ('terceros', '1D', 'Mejor 3° BEFIJ')),
    82: (('primeros', 'G', '1° Grupo G'), ('terceros', '1G', 'Mejor 3° AEHIJ')),
    83: (('segundos', 'K', '2° Grupo K'), ('segundos', 'L', '2° Grupo L')),
    84: (('primeros', 'H', '1° Grupo H'), ('segundos', 'J', '2° Grupo J')),
    85: (('primeros', 'B', '1° Grupo B'), ('terceros', '1B', 'Mejor 3° EFGIJ')),
    86: (('primeros', 'J', '1° Grupo J'), ('segundos', 'H', '2° Grupo H')),
    87: (('primeros', 'K', '1° Grupo K'), ('terceros', '1K', 'Mejor 3° DEIJL')),
    88: (('segundos', 'D', '2° Grupo D'), ('segundos', 'G', '2° Grupo G')),
}


def terceros_por_partido(terceros_por_grupo):
    grupos = ''.join(sorted(terceros_por_grupo))
    asignacion = ANNEX_C_TABLE.get(grupos)
    if not asignacion:
        return {}
    return {
        ANNEX_C_COLUMN_TO_MATCH[columna]: terceros_por_grupo.get(grupo)
        for columna, grupo in zip(ANNEX_C_COLUMNS, asignacion)
        if grupo in terceros_por_grupo
    }
