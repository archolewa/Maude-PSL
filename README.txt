Usage: ./psl.py <FILENAME>.psl

The program will generate two files: 
<FILENAME>.pslmaude, <FILENAME>.maude.

<FILENAME>.pslmaude is a transitionary file that is loaded into Maude, and can be 
ignored
by the user (unless they need to investigate an error message). <FILENAME>.maude 
contains the Maude-NPA modules that can be loaded into the Maude-NPA.

Note that although the translation program itself works with Maude 2.6, the Maude-NPA 
version
that the generated modules are compatible with relies on a version of Maude that is
not-quite-ready for release. Therefore, in addition to the translation code, included
are experimental versions of Maude, the Maude prelude, and the Maude-NPA that these 
modules are compatible with. 

To load <FILENAME>.maude into the Maude-NPA, type:

./maude96c -no-prelude prelude.maude maude-npa.maude <FILENAME>.maude

Dependent Python libraries:
fuzzywuzzy
