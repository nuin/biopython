update_from_cvs:
  @echo "cvs to git migration - refer to this tutorial: http://www.kernel.org/pub/software/scm/git/docs/v1.4.4.4/cvs-migration.html"
  @echo `date`> last_cvs_update.txt
  @git cvsimport -v -d :pserver:cvs@code.open-bio.org:/home/repository/biopython -C . biopython
