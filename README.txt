Usage: ./psl.py <FILENAME>.psl

or

./psl.sh <FILENAME>.sh

The difference is that the second command also automatically loads the 
generated Maude file into Maude-NPA, along with all the other files that
Maude-NPA needs to run properly, using the version of Maude included in the 
repository (maude27 as of May 14 2015). Note that if you invoke the shell
script, then Maude-NPA will be loaded whether or not the PSL script 
successfully executes. So invoking psl.py is recommended until the 
specification is well-formed.

The program will generate one files: 
<FILENAME>.maude.

<FILENAME>.maude 
contains the Maude-NPA modules that can be loaded into the Maude-NPA.

Note that although the translation program itself works with Maude 2.6, the 
Maude-NPA 
version
that the generated modules are compatible with relies on a version of Maude 
that is
not-quite-ready for release. Therefore, in addition to the translation code, 
included
is an experimental version of Maude, the Maude prelude, and the Maude-NPA that 
these modules are compatible with. 

To load <FILENAME>.maude into the Maude-NPA, type:

./maude27 -no-prelude prelude.maude maude-npa.maude <FILENAME>.maude

For more details about PSL, see psl_description.pdf (a draft of Andrew Cholewa's
Spring 2015 Masters Thesis at University of Illinois at Urbana-Champaign), 
included with this repository.

