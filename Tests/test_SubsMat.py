import cPickle
import sys
from Bio import SubsMat
from Bio.SubsMat import FreqTable, MatrixInfo

f = sys.stdout
ftab_prot = FreqTable.read_count(open('SubsMat/protein_count.txt'))
ctab_prot = FreqTable.read_freq(open('SubsMat/protein_freq.txt'))
f.write("Check differences between derived and true frequencies for each\n")
f.write("letter. Differences should be very small\n")
for i in ftab_prot.alphabet.letters:
    f.write("%s %f\n" % (i, abs(ftab_prot[i] - ctab_prot[i])))
    
acc_rep_mat = cPickle.load(open('SubsMat/acc_rep_mat.pik'))
acc_rep_mat = SubsMat.SeqMat(acc_rep_mat)
obs_freq_mat = SubsMat._build_obs_freq_mat(acc_rep_mat)
ftab_prot2 = SubsMat._exp_freq_table_from_obs_freq(obs_freq_mat)
obs_freq_mat.print_mat(f=f,format=" %4.3f")


f.write("Diff between supplied and matrix-derived frequencies, should be small\n")
for i in ftab_prot.keys():
    f.write("%s %.2f\n" % (i,abs(ftab_prot[i] - ftab_prot2[i])))

s = 0.
f.write("Calculating sum of letters for an observed frequency matrix\n")
obs_freq_mat.all_letters_sum()
for i in obs_freq_mat.sum_letters.keys():
    f.write("%s\t%.2f\n" % (i, obs_freq_mat.sum_letters[i]))
    s += obs_freq_mat.sum_letters[i]
f.write("Total sum %.2f should be 1.0\n" % (s))
lo_mat_prot = \
SubsMat.make_log_odds_matrix(acc_rep_mat=acc_rep_mat,round_digit=1) #,ftab_prot
f.write("\nLog odds matrix\n")
lo_mat_prot.print_mat(f=f,format=" %.2f",alphabet='AVILMCFWYHSTNQKRDEGP')

f.write("\nTesting MatrixInfo\n")
for i in MatrixInfo.available_matrices:
    mat = SubsMat.SeqMat(getattr(MatrixInfo,i))
    f.write("\n%s\n------------\n" % i)
    mat.print_mat(f=f)
