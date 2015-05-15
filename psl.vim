" Vim syntax file
" Language: Maude-PSL
" Maintainer: Andrew Cholewa <acholew2@illinois.edu>
" A slightly modified version of the syntax file used for the Maude language:
"
" Language:      Maude <http://maude.cs.uiuc.edu/>
" Maintainer:    Steven N. Severinghaus <sns@severinghaus.org>
" Last Modified: 2005-02-03 " Version: 0.1
" To install, copy (or link) this file into the ~/.vim directory 
" and add the following to your ~/.vimrc file

" au BufRead,BufNewFile *.maude set filetype=maude
" au BufRead,BufNewFile *.kmaude set filetype=maude
" au BufRead,BufNewFile *.k set filetype=maude
" au BufRead,BufNewFile *.m set filetype=maude
" au! Syntax maude source maude.vim
" syn on


" Quit if syntax file is already loaded
if version < 600
  syntax clear
elseif exists("b:current_syntax")
  finish
endif

command! -nargs=+ MaudeHiLink hi def link <args>

"Matches words that start with an uppercase letter.
"Added by Andrew Cholewa
"This is meant to allow variable names to stick out, assuming the coder
"follows the convention of capitalizing the first character of their variable
"names.
"Match at least one upper-case letter followed by 0 or more digits
"So variables are of the form T T1 T2 SPEC 
syn match variableName      /\<\u\+\d\{-}\>/
"Match at least one upper-case letter followed by a lower-case letter followed
"by zero or more word characters.
"Sorts are of the form Sortname SortName 
syn match maudeSorts      /\<\u\l\w\{-}\>/
"Added by Andrew Cholewa
"This is meant to make the parenthesis stand out, which is very important
"considering how much Maude relies on parenthesis.
syn match parenthesis       /(/
syn match parenthesis       /)/
"The end result of the matching patterns above is to make the operators stick
"out more (roughly, the non-highlighted text are the user-defined
"operators).
"End Material added by Andrew Cholewa
syn keyword maudeModule     mod fmod omod endm endfm endm is endkm
syn keyword maudeImports    protecting including extending
syn keyword maudeSortDecl   sort sorts subsort subsorts
syn keyword maudeStatements op ops var vars eq ceq rl crl rule macro context configuration mb cmb if fi then else
"syn match   maudeFlags      "\[.*\]"
syn keyword maudeCommands   reduce red rewrite rew parse frewrite frew search
syn match   maudeComment    "\*\*\*.*"
syn match   maudeComment    "---.*"
syn region  maudeComment    start="/\*"  end="\*/" contains=maudeTodo,@Spell
syn region  maudeComment    start="---("  end="---)" contains=maudeTodo,@Spell
syn match   maudeComment    "//.*" contains=maudeTodo,@Spell
syn match   maudeStatements    "->"
syn match   maudeStatements    "|"
syn match   maudeStatements    ":"
"syn match   maudeOps        "^\s*subsorts[^<]*<"hs=e-1
"syn match   maudeOps        "^\s*ceq[^=]*="
syn match   maudeOps        "="
syn match   maudeOps        "\.\s*$"

"syn keyword maudeSorts      K KResult KLabel KResultLabel List Bag Set Map
"syn keyword maudeSorts      NeList NeMap NeBag NeSet
"syn keyword maudeSorts      KProper KProperLabel NeKProperList
"syn keyword maudeSorts      CellLabel ListItem BagItem SetItem MapItem

syn keyword maudeAttrs      assoc comm idem iter id left-id right-id strat memo
syn keyword maudeAttrs      prec gather format ctor config object msg frozen
syn keyword maudeAttrs      poly special label metadata owise nonexec
syn keyword maudeAttrs      seqstrict strict structural hybrid nondet bidirectional large
syn keyword maudeAttrs      latex

syn match maudeStatements   "_" 
syn match maudeStatements   "?"
syn match maudeStatements   "\.\.\." 

"syn keyword maudeLiteral    Bool Int Float Nat Qid Id
"syn keyword maudeLiteral    Zero NzNat NzInt NzRat Rat FiniteFloat
"syn keyword maudeLiteral    String Char FindResult DecFloat
syn keyword maudeLiteral    andBool orBool xorBool notBool impliesBool
"syn keyword maudeLiteral    sNat
syn keyword maudeLiteral    true false
syn match   maudeLiteral    "\<\(0[0-7]*\|0[xX]\x\+\|\d\+\)[lL]\=\>"
syn match   maudeLiteral    "\(\<\d\+\.\d*\|\.\d\+\)\([eE][-+]\=\d\+\)\=[fFdD]\="

syn keyword maudeTodo       contained TODO FIXME XXX NOTE BUG

syn region  maudeString     start=+"+ end=+"+ contains=@Spell

MaudeHiLink maudeModule     PreProc
MaudeHiLink maudeImports    PreProc
MaudeHiLink maudeAttrs      Comment
MaudeHiLink maudeStatements Keyword
MaudeHiLink maudeModules    String
MaudeHiLink maudeComment    Comment
MaudeHiLink maudeSortDecl   Keyword
MaudeHiLink maudeOps        Special
MaudeHiLink maudeCommands   Special
MaudeHiLink maudeFlags      Comment
MaudeHiLink maudeSorts      PreProc
MaudeHiLink maudeLiteral    String
MaudeHiLink maudeTodo       Todo
MaudeHiLink maudeString     String
"Added by Andrew Cholewa
MaudeHiLink variableName    Identifier
MaudeHiLink parenthesis     Comment
"hi def     maudeMisc       term=bold cterm=bold gui=bold

delcommand MaudeHiLink
  
let b:current_syntax = "maude"

"EOF vim: tw=78:ft=vim:ts=8
