from Bio.SeqUtils import IsoelectricPoint, ProtParam

X = ProtParam.ProteinAnalysis("MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNGGHFLRILPDGTVDGTRDRSDQHIQLQLSAESVGEVYIKSTETGQYLAMDTSGLLYGSQTPSEECLFLERLEENHYNTYTSKKHAEKNWFVGLKKNGSCKRGPRTHYGQKAILFLPLPV")
print "isoelectric point for this protein: %.3f" % X.isoelectric_point()
