import string
import math
def Tm_staluc(s,dnac=50,saltc=50,rna=0):
    """Returns DNA/DNA tm using nearest neighbor thermodynamics. dnac is
    DNA concentration [nM] and saltc is salt concentration [mM].
    rna=0 is for DNA/DNA (default), for RNA, rna should be 1.
    Sebastian Bassi <sbassi@genesdigitales.com>"""
    
    #Credits: 
    #Main author: Sebastian Bassi <sbassi@genesdigitales.com>
    #Overcount function: Greg Singer <singerg@tcd.ie>
    #Based on the work of Nicolas Le Novere <lenov@ebi.ac.uk> Bioinformatics. 17:1226-1227(2001)

    #This function returns better results than EMBOSS DAN because it uses updated
    #thermodinamics values and take into account inicialization parameters from SantaLucia
    #works (1998).
    
    #Things to do:
    #+Add a function to detect complementary sequences. Change K according to result.
    #+Add support for heteroduplex (see Sugimoto et al. 1995).
    #+Correction for Mg2+. Now supports only monovalent ions.
    #+Put thermodinamics table in a external file for users to change at will
    #+Add support for danglings ends (see Le Novele. 2001) and mismatches.
    
    dh=0 #DeltaH. Enthalpy
    ds=0 #deltaS Entropy

    def tercorr(stri):
        deltah=0
        deltas=0
        if rna==0:
            #DNA/DNA
            #Allawi and SantaLucia (1997). Biochemistry 36 : 10581-10594
            if stri[0]=="G" or stri[0]=="C":
                deltah=deltah-0.1
                deltas=deltas+2.8
            elif stri[0]=="A" or stri[0]=="T":
                deltah=deltah-2.3
                deltas=deltas-4.1
            if stri[-1]=="G" or stri[-1]=="C":
                deltah=deltah-0.1
                deltas=deltas+2.8
            elif stri[-1]=="A" or stri[-1]=="T":
                deltah=deltah-2.3
                deltas=deltas-4.1
            dhL=dh+deltah
            dsL=ds+deltas
            return dsL,dhL
        elif rna==1:
            #RNA
            if stri[0]=="G" or stri[0]=="C":
                deltah=deltah-3.61
                deltas=deltas-1.5
            elif stri[0]=="A" or stri[0]=="T" or stri[0]=="U":
                deltah=deltah-3.72
                deltas=deltas+10.5
            if stri[-1]=="G" or stri[-1]=="C":
                deltah=deltah-3.61
                deltas=deltas-1.5
            elif stri[-1]=="A" or stri[-1]=="T" or stri[0]=="U":
                deltah=deltah-3.72
                deltas=deltas+10.5
            dhL=dh+deltah
            dsL=ds+deltas
            # print "delta h=",dhL
            return dsL,dhL

    def overcount(st,p):
        """Returns how many p are on st, works even for overlapping"""
        ocu=0
        x=0
        while 1:
            try:
                i=st.index(p,x)
            except ValueError:
                break
            ocu=ocu+1
            x=i+1
        return ocu

    sup=string.upper(s)
    R=1.987 # universal gas constant in Cal/degrees C*Mol
    vsTC,vh=tercorr(sup)
    vs=vsTC
    
    k=(dnac/4.0)*1e-9
    #With complementary check on, the 4.0 should be changed to a variable.
    
    if rna==0:
        #DNA/DNA
        #Allawi and SantaLucia (1997). Biochemistry 36 : 10581-10594
        vh=vh+(overcount(sup,"AA"))*7.9+(overcount(sup,"TT"))*7.9+(overcount(sup,"AT"))*7.2+(overcount(sup,"TA"))*7.2+(overcount(sup,"CA"))*8.5+(overcount(sup,"TG"))*8.5+(overcount(sup,"GT"))*8.4+(overcount(sup,"AC"))*8.4
        vh=vh+(overcount(sup,"CT"))*7.8+(overcount(sup,"AG"))*7.8+(overcount(sup,"GA"))*8.2+(overcount(sup,"TC"))*8.2
        vh=vh+(overcount(sup,"CG"))*10.6+(overcount(sup,"GC"))*9.8+(overcount(sup,"GG"))*8+(overcount(sup,"CC"))*8
        vs=vs+(overcount(sup,"AA"))*22.2+(overcount(sup,"TT"))*22.2+(overcount(sup,"AT"))*20.4+(overcount(sup,"TA"))*21.3
        vs=vs+(overcount(sup,"CA"))*22.7+(overcount(sup,"TG"))*22.7+(overcount(sup,"GT"))*22.4+(overcount(sup,"AC"))*22.4
        vs=vs+(overcount(sup,"CT"))*21.0+(overcount(sup,"AG"))*21.0+(overcount(sup,"GA"))*22.2+(overcount(sup,"TC"))*22.2
        vs=vs+(overcount(sup,"CG"))*27.2+(overcount(sup,"GC"))*24.4+(overcount(sup,"GG"))*19.9+(overcount(sup,"CC"))*19.9
        ds=vs
        dh=vh
        
    else:
        #RNA/RNA hybridisation of Xia et al (1998)
        #Biochemistry 37: 14719-14735         
        vh=vh+(overcount(sup,"AA"))*6.82+(overcount(sup,"TT"))*6.6+(overcount(sup,"AT"))*9.38+(overcount(sup,"TA"))*7.69+(overcount(sup,"CA"))*10.44+(overcount(sup,"TG"))*10.5+(overcount(sup,"GT"))*11.4+(overcount(sup,"AC"))*10.2
        vh=vh+(overcount(sup,"CT"))*10.48+(overcount(sup,"AG"))*7.6+(overcount(sup,"GA"))*12.44+(overcount(sup,"TC"))*13.3
        vh=vh+(overcount(sup,"CG"))*10.64+(overcount(sup,"GC"))*14.88+(overcount(sup,"GG"))*13.39+(overcount(sup,"CC"))*12.2
        vs=vs+(overcount(sup,"AA"))*19.0+(overcount(sup,"TT"))*18.4+(overcount(sup,"AT"))*26.7+(overcount(sup,"TA"))*20.5
        vs=vs+(overcount(sup,"CA"))*26.9+(overcount(sup,"TG"))*27.8+(overcount(sup,"GT"))*29.5+(overcount(sup,"AC"))*26.2
        vs=vs+(overcount(sup,"CT"))*27.1+(overcount(sup,"AG"))*19.2+(overcount(sup,"GA"))*32.5+(overcount(sup,"TC"))*35.5
        vs=vs+(overcount(sup,"CG"))*26.7+(overcount(sup,"GC"))*36.9+(overcount(sup,"GG"))*32.7+(overcount(sup,"CC"))*29.7
        ds=vs
        dh=vh

    ds=ds-0.368*(len(s)-1)*math.log(saltc/1e3)
    tm=((1000* (-dh))/(-ds+(R * (math.log(k)))))-273.15
    # print "ds="+str(ds)
    # print "dh="+str(dh)
    return tm


