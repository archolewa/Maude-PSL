"""
Maude-PSL, Version: [1.0] [May 15th 2015]
Copyright (c) 2015, University of Illinois
All rights reserved.
Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:
* Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation 
and/or other materials provided with the distribution.
* Neither the name of the University of Illinois nor the names of its contributors 
may be used to endorse or promote products derived from this software without 
specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
-----------------------------------------------------------------------------------------------------------
Copyright (c) 2015. To the extent that a federal employee is an author of 
a portion of the software or a derivative work thereof, no copyright is 
claimed by the United States Government, as represented by the Secretary 
of the Navy ("GOVERNMENT") under Title 17, U.S. Code. All Other Rights Reserved.
Permission to use, copy, and modify this software and its documentation is 
hereby granted, provided that both the copyright notice and this permission 
notice appear in all copies of the software, derivative works or modified 
versions, and any portions thereof, and that both notices appear in 
supporting documentation.
GOVERNMENT ALLOWS FREE USE OF THIS SOFTWARE IN ITS "AS IS" CONDITION AND 
DISCLAIM ANY LIABILITY OF ANY KIND FOR ANY DAMAGES WHATSOEVER RESULTING 
FROM THE USE OF THIS SOFTWARE.
GOVERNMENT requests users of this software to return modifications, 
improvements or extensions that they make to: 
maudenpa@chacs.nrl.navy.mil]
-or-
Naval Research Laboratory, Code 5543
4555 Overlook Avenue, SW
Washington, DC 20375
"""
#!/usr/bin/python
from __future__ import print_function
import itertools
import pslErrors
import pslTree
import re
import subprocess
import sys
import os
#I was  going to use this to improve some of the error messages, but I haven't had time to write awesome messages.
#However, if I import this, it always prints a warning about using the slow fuzzy match. While that doesn't affect 
#the running of the program, it is mildly annoying.
#from fuzzywuzzy import fuzz

"""
    Note: If at any time an error has a line number of -1, this means that
    there was a problem with some automatically generated code, in which case
    there's an error that I missed while performing initial error checking.
    
    To use: type the command ./psl.py FILENAME.psl
    Options:
        -m PATH/TO/MAUDE/EXECUTABLE use to specify the path to the maude 
        executable you'd like to use. If option not provided, defaults to just 
        using the 'maude' command. We'll probably have additional options for 
        such things as loading the specification directly into the maude-npa, 
        choosing a different version of maude, choosing other maude files to 
        load into maude, etc, but that's a task for the future.

    Some of the errors that the Python code needs to check for include:
    0. Make sure parenthesis are balanced. done
    1. make sure that every In has accompanying Out and
        strand execution statements. So, if there's a single term left, it 
        won't be an In.
        
    2. Make sure the subsort keywords and the < are correct
    3. Check the high-level syntax. 
        a. Make sure that there are no illegal operators: 
                i. _,_
                ii. _|->_
                iii. _._
                iv. In, Out, Def.
                v. anything containing a $.
                vi. _=>_
                vii. _executes protocol
                viii. Intruder learns_
                ix. without:
                x. _|-_
                xi. Any operator containing unbalanced parenthesis or curly 
                braces Basically, we assume that the user-defined syntax is 
                disjoint from 
                anything that starts a new statement, because it simplifies
                checking for missing periods, and from anything that appears
                next to user-defined terms
                in order to avoid ambiguities with the high-level syntax. 
                Note: This may be more restrictive than necessary, but we can
                relax these requirements later.

    QUESTION: Do we want to declare the macros globally, since ostensibly
    they could show up anywhere?
"""

#TODO: Replace the role names with NAME_OF_MODULE-ROLENAME, and add
#NAME_OF_MODULE-ROLENAME as constants of sort Role to the theory.
#Also, for composition, automatically replace the role names with the same
#generated constant.

#Terms are "blackboxes" of user-defined syntax. For simplicity, we assume
#that all tokens in the user defined syntax are disjoint from all tokens
#in the higher-level syntax.
#We may be able to relax this restriction, depending on how much I actually
#need to know at the parser level.


MAUDE_DEFAULT = 'maude'

MAUDE_FAN = '/Users/fan/Documents/maude/maude.darwin64'

MAUDE_COMMAND = './maude27' 
NO_PRELUDE = '-no-prelude'
PRELUDE = 'prelude.maude'
FULL_MAUDE = 'full-maude.maude'
#MAUDE_COMMAND = 'maude'

NPA_SYNTAX = 'NPA-Syntax.maude'
TRANSLATION_FILE = 'psl.maude'

CODE = 0
LINE_NUM = 1
STATE_SPACE_REDUCTION_VARIANTS = ['state-space-reduction:', 'State-space-reduction:'] 
END_LINE = ['.', 'without:', 'Without:', 'avoid:', 'Avoid:'] + STATE_SPACE_REDUCTION_VARIANTS

def nonzero_nats():
    """
    A generator that yields as many natural numbers as you need (up to 
    physical limitations).
    """
    count = 1
    while True:
        yield count
        count += 1


def number_lines(lines):
    """
    Given an iterable of PSL lines, returns an iterable of pairs pairing
    each line with its line number.
    """
    return zip(lines, nonzero_nats())



def pairwise(iterable):
    """
    Given an iterable: [m_1, m_2, ..., m_n] returns a list of pairs:
    [(m_1, m_2), (m_2, m_3), ...(m_{n-1}, m_n), (m_n, m_n)].
    If n == 1, then it returns the list [(m_1, m_1)]. If n == 0, then it 
    returns an empty list.
    """
    listIt = list(iterable)
    try:
        result = zip(listIt, listIt[1:]) + [(listIt[-1], listIt[-1])]
    except IndexError:
        result = []
    return result



singleLineComment = re.compile(r'//.*$')
startSpec = re.compile(r'spec \S+ is')

def lex_code(pslFile):
    """
    Given an iterable of lines of PSL code, returns a dictionary mapping
    section names to lists of statements.
    """
    sectionStmts = {heading:[] for heading in pslTree.SECTION_HEADINGS}
    numberedLines = [(tokenize(line), num) for line, num in 
            number_lines(pslFile)]
    statement = pslTree.Statement()
    #List of pairs of comment token with line number. 
    startComment = []
    errorMsgs = []
    for i in range(len(numberedLines)):
        line, num = numberedLines[i]
        for j in range(len(line)):
            token = line[j].strip()
            try:
                nextToken = line[j+1]
            except IndexError:
                try:
                    nextToken = numberedLines[i+1][0][0]
                except IndexError:
                    nextToken = nextNextToken = ''
                else:
                    try:
                        nextNextToken = numberedLines[i+1][0][1]
                    except IndexError:
                        try:
                            nextNextToken = numberedLines[i+2][0][0]
                        except IndexError:
                            nextNextToken = ''
            else:
                try:
                    nextNextToken = line[j+2]
                except IndexError:
                    try:
                        nextNextToken = numberedLines[i+1][0][0]
                    except IndexError:
                        nextNextToken = ''
            if token == r'/*':
                startComment.append((token, num))
            elif token == r'*/':
                try:
                    if startComment[-1][0] == r'/*': 
                        startComment = startComment[:-1]
                        continue
                    else: 
                        raise IndexError()
                except IndexError:
                    raise errorMsgs.append(' '.join([pslErrors.error, 
                        pslErrors.color_line_number(num), 
                        "Unexpected end comment token:", 
                        pslErrors.color_token(token)]))
            if startComment or re.match(singleLineComment, token): 
                continue
            elif not sectionStmts['Start'] and re.match(startSpec, token):
                stmt = pslTree.Statement([token], [num])
                sectionStmts["Start"].append(stmt)
                continue
            elif is_start_of_section(token, nextToken): 
                section = token
            elif token in END_LINE and not protocol_step(nextToken, nextNextToken):
                statement.append(token, num)
                sectionStmts[section].append(statement)
                statement = pslTree.Statement()
            else: 
                statement.append(token, num)
    for token, num in startComment:
       errorMsgs.append(' '.join([pslErrors.error, pslErrors.color_line_number(num), 
           "Dangling comment token:", pslErrors.color_token(token)]))
    if errorMsgs:
        raise pslErrors.LexingError('\n'.join(errorMsgs))
    #Removes some unnecessary end of comment statements that are still floating around.
    for key in sectionStmts:
        for stmt in sectionStmts[key]:
            stmt.tokens = [token for token in stmt.tokens if token != '*/'] 
    return sectionStmts


def protocol_step(nextToken, nextNextToken):
    """
    Returns true if nextToken and nextNextToken correspond to what's expected as the second and third tokens in a protocol
    step. This is important to distinguish between statement terminating periods, and the periods in each protocol step statement.
    """
    try:
        return nextNextToken == '->' and nextToken not in pslTree.TOP_LEVEL_TOKENS
    except IndexError:
        return False


def type_check_sectionStmts(sectionStmts):
    """
    Checks to make sure that the statements in each section are in fact statement objects. For debugging purposes only.
    """
    for section in sectionStmts:
        for statement in sectionStmts:
            assert(isinstance(statement, pslTree.Statement)), "statement is not a pslTree.Statement: %s" % statement


def tokenize(line):
    """
    Splits the passed PSL line into a list of tokens, and returns those tokens.
    """
    return [token for token in re.split(pslTree.Token.tokenizer, line.strip()) if token]


def is_start_of_section(token, nextToken):
    return token in pslTree.SECTION_HEADINGS and (token != 'Intruder' or 
            nextToken != 'learns')


def maudify():
    """
    Given a pslFilePath, and a set of conversion options(TBD), converts the PSL
    file specification into a Maude-NPA specification.  options:
         -m Allows you to specify a path to the maude executable you'd like
                         to execute
        The steps to doing this are:
        1. Error check the high level syntax.
        2. Annotate the file with line numbers, and wrap the specification in 
        parenthesis
        3. Feed the annotated file into Maude, along with the Maude
        conversation file.  
    """
    try:
        pslFilePath = sys.argv[1]
    except IndexError:
        print("Usage: ./psl.py FILENAME.psl")
        return
    try:
        options = sys.argv[2:]
    except IndexError:
        pass
    else:
        for option, argument in zip(options, options[1:]):
            if option == "-m":
                global MAUDE_COMMAND, PRELUDE
                MAUDE_COMMAND = argument
                NO_PRELUDE = ''
                PRELUDE = ''
    fileName = os.path.basename(pslFilePath).split('.')[0]
    with open(pslFilePath, 'r') as f:
        parseTree = parse_code(lex_code(f))
    theoryFileName = build_theory(parseTree, os.path.dirname(pslFilePath), fileName) 
    #TODO: Need to invoke different functions depending on whether we're doing protocol composition, or normal PSL translation.
    intermediate = gen_intermediate(parseTree, theoryFileName) 
    gen_NPA_code(intermediate, theoryFileName, parseTree)

DEF_KEY_ROLE = 0
DEF_KEY_TERM = 1
DEF_SHORTHAND = 0
DEF_LINE_NUM = 1
def gen_intermediate(parseTree, theoryFileName):
    """
    Generates the maude code needed to translate a PSL specification into a trio of Maude-NPA module.
    Returns the code as a list of lines.
    """
    code = ['load psl.maude', ' '.join(['load', theoryFileName]), 'mod INTERMEDIATE is', 'protecting TRANSLATION-TO-MAUDE-NPA .', 
            'protecting PROTOCOL-EXAMPLE-SYMBOLS .']
    defPairs = []
    for defNode in parseTree.get_protocol().get_defs():
        defPairs.extend(defNode.def_pairs())
    defMap = {}
    for defPair in defPairs:
        if (defPair.role(), defPair.term()) in defMap:
            otherDef = defMap[(defPair.role(), defPair.term())]
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(defPair.lineNum) + ",", 
                otherDef[DEF_LINE_NUM], "Term", pslErrors.color_token(defPair.term()), 
                "has multiple shorthands: ", pslErrors.color_token(defPair.shorthand()) + ",", 
                pslErrors.color_token(otherDef[DEF_SHORTHAND])]))
        else:
            defMap[(defPair.role(), defPair.term())] = (defPair.shorthand(), defPair.lineNum)
    shorthandSortMap = compute_sorts(defMap, theoryFileName, parseTree)
    code.extend([' '.join(['op', shorthand, ':', '->', sort, '.']) for shorthand, sort in shorthandSortMap.items()])
    code.append('endm')
    code.append('rew')
    code.extend(['Specification', '{'])
    protocol = parseTree.get_protocol()
    code.extend(stmt for stmt in protocol.translate() if stmt)
    intruder = parseTree.get_intruder()
    code.extend([stmt for stmt in intruder.translate() if stmt])
    attacks = parseTree.get_attacks()
    code.extend([stmt for stmt in attacks.translate() if stmt])
    code.append('}')
    #Empty StrandData for protocols
    code.append('[mt]')
    #Empty strand set for intruders
    code.append('[empty]')
    if defMap:
        defs = ', '.join([' '.join([''.join(['(', shorthandLineNum[DEF_SHORTHAND], ', ', str(shorthandLineNum[DEF_LINE_NUM]), ')']), ':=', 
            roleTermPair[DEF_KEY_TERM]]) for roleTermPair, shorthandLineNum in defMap.items()])
    else:
        defs = '$noDefs'
    code.append(' '.join(['[', '$makeIdem($checkWellFormed(', defs, '))', ']']))
    code.append('.')
    return code

def gen_NPA_code(maudeCode, theoryFileName, parseTree):
    maudeCommand = [MAUDE_COMMAND, NO_PRELUDE, '-no-banner', '-no-advise', '-no-wrap', PRELUDE, NPA_SYNTAX, theoryFileName, 
            TRANSLATION_FILE]
    maudeExecution = subprocess.Popen(maudeCommand, stdout=subprocess.PIPE, 
        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = maudeExecution.communicate('\n'.join(maudeCode))
    if stderr:
        errors = []
        #Expected error pattern:
        #Warning: <standard input>, line N : <error message> 
        for line in [line.strip() for line in stderr.split('\n') if line.strip()]:
            try:
                _,lineNum, error = line.split(':')
            except ValueError:
                print(stderr)
                assert False
            #expected pattern currently in lineNum:
            #<standard input>, line N
            lineNum = int(lineNum.split()[-1])
            #Maude's lines on the terminal start counting from 1, but Python lists start counting at 0.
            pslLine = maudeCode[lineNum-1]
            #pattern of psl statements inside Maude code
            #blah blah . [ num ] 
            try:
                pslLineNum = int(pslLine.split()[-2])
            except (IndexError, ValueError): 
                pass
            else:
                bracketIndex = pslLine.rfind('[')
                errors.append(' '.join([pslErrors.error, pslErrors.color_line_number(pslLineNum), error, "\n\tCode: ", 
                    pslLine[:bracketIndex]]))
        raise pslErrors.SyntaxError('\n'.join(errors))
    else:
        #rewrite in <module-name> : Maude term
        #rewrites: blah blah
        #result ModuleNPA: maude module (if things go right)
        #result [ModuleNPA] : vomit (if things go wrong)
        #command, _, result = [line.replace("Maude>", "") for line in stdout.split('\n')]
        #_, sortName = result[:result.index(':')
        desiredResult = "result ModuleNPA:"
        try:
            index = stdout.index(desiredResult) + len(desiredResult)
        except ValueError:
            errorResult = "result [TranslationData]:"
            errorIndex = stdout.index(errorResult) + len(errorResult)
            process_error(stdout[errorIndex:], parseTree)
        else:
            endOfModule = stdout.rfind("Maude>")
            module = '\n' + stdout[index:endOfModule].strip()
            with open(theoryFileName, 'a') as maudeFile:
                maudeFile.write(module)
                maudeFile.write('\nselect MAUDE-NPA .')

def process_error(error, parseTree):
    """
    Given a partially evaluated PSL specification, extracts the offending error term, and extracts from the error term the information 
    need for a usable error message. Then raises a TranslationError containing said usable error message.
    """
    errorTermStart = error.index("$$$")
    errorType, errorTerm = error[errorTermStart:].split('(', 1)
    numParens = 1
    endOfTerm = compute_end_of_term(errorType, errorTerm)
    errorTerm = errorTerm[:endOfTerm]
    if errorType == "$$$infiniteIdem":
        invalidMapping, lineNumbers = errorTerm.rsplit(',', 1)
        lineNumbers = [number.strip() for number in lineNumbers.split(':')]
        raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(','.join(lineNumbers)),
            "The substitution: ", invalidMapping, "cannot be made idempotent."]))
    elif errorType.strip() == "$$$malformedDefs":
        errorDefs = []
        for error in errorTerm.split("$$;;;;$$"):
            pair, lineNumber = error.split("$$,$$")
            lineNumber = lineNumber.replace(")", '')
            errorDefs.append(' '.join([pslErrors.error, pslErrors.color_line_number(lineNumber.strip()), 
                                         #Stripping off the () around the definition
                "Malformed Definition:", pslErrors.color_token(pair[1:-1])]))
        raise pslErrors.TranslationError('\n'.join(errorDefs))
    elif errorType.strip() == "$$$malformedTerm":
        errorTerm, lineNumber =  errorTerm.rsplit(',', 1)
        raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNumber.strip()), "Malformed term:", errorTerm]))
    elif errorType.strip() == "$$$notAFunction":
        errorMappings = errorTerm.split("$$$;;;$$$")
        errorMsg = []
        for error in errorMappings:
            var, results = [string.strip() for string in error.split('|->')]
            problemTerms = []
            lineNumbers = []
            for result in [r.strip() for r in results.split('}$') if r.strip()]:
                result = result.replace('${', '')
                startLineNum = result.rindex(';')+1
                lineNumber = result[startLineNum:].strip()
                result = result[:startLineNum-1].strip()
                problemTerms.append(result)
                lineNumbers.append(lineNumber)
            errorMsg.append(''.join([pslErrors.errorNoLine, " Substitution does not",
                " define a function. Variable: ", pslErrors.color_token(var),
                " maps to the terms:\n\t", '\n\t'.join([' Line: '.join([
                    pslErrors.color_token(term),
                    pslErrors.color_line_number(lineNum)]) for term, lineNum
                    in zip(problemTerms, lineNumbers)])]))
        raise pslErrors.TranslationError('\n'.join(errorMsg)) 
    elif errorType.strip() == "$$$invalidSorting":
        var, termLineNum = [s.strip() for s in errorTerm.split('|->')]
        var, variableSort = var.split(':')
        termLineNum = termLineNum.replace('${', '').replace('}$', '')
        lineNumberIndex = termLineNum.rindex(';')+1
        lineNum = termLineNum[lineNumberIndex:].strip()
        term = termLineNum[:lineNumberIndex-1].strip()
        raise pslErrors.TranslationError(' '.join([pslErrors.error, 
            pslErrors.color_line_number(lineNum), "Variable", 
            pslErrors.color_token(var), "has sort", 
            pslErrors.color_token(variableSort), "but term",
            pslErrors.color_token(term), "does not."]))





def compute_end_of_term(errorType, errorTerm):
    """
    Given the start of term that contains the errorTerm as a subterm (and which starts with the first argument of the error term), 
    finds the index of the end of the error term (i.e. the closing parenthesis) and returns that index.
    If a closing parenthesis is not found, a ValueError is raised.
    """
    endOfTerm = 0
    numParens = 1
    for character in errorTerm:
        if character == '(':
            numParens += 1
        elif character == ')':
            numParens -= 1
            if not numParens:
                return endOfTerm
        endOfTerm += 1
    raise ValueError(' '.join(["End of error term of type: ", errorType, "not found when trying to extract the term from:", errorTerm]))
           
MAX_ITERATIONS = 100
def compute_sorts(defMap, syntaxFileName, parseTree):
    """
    Computes the sorts of the user-defined shorthand. 
    
    defMap is expected to be a dictionary with the following format:
    (role, term) : (shorthand, lineNumber) 
    where term is the term whose sort is to be computed, shorthand is the user-defined shorthand, and line number is the line number in 
    PSL at which the term appears.
    pslSyntaxFileName is the name of the maude file that contains the user-defined syntax (this is the partially filled file containing the translated NPA code).

    Returns a dictionary mapping shorthand to their respective sorts.
    """
    is_function(defMap)
    role_variables_correct(defMap, parseTree)
    SHORTHAND = 0
    LINE_NUMBER = 1
    ROLE = 0
    TERM = 1
    termRolePairs = sorted(defMap.keys(), key=lambda pair: defMap[pair][DEF_LINE_NUM])
    #Note: We need to split the shorthand mappings into shorthand we can figure out (i.e. shorthand that doesn't depend on other
    #shorthand, and shorthand that does. Then we iteratively grow the shorthand that doesn't depend on others as we compute the
    #sorts of the indepedent shorthand, until we've computed the sorts of all the shorthand.
    shorthand = {shorthand for shorthand, lineNumber in defMap.values()}
    dependentShorthand = {(role, term):shorthandLineNum for ((role, term), shorthandLineNum) in defMap.iteritems() if
        set(term.split()).intersection(shorthand)}
    independentShorthand = {roleTerm:defMap[roleTerm] for roleTerm in defMap if not roleTerm in dependentShorthand}
    knownShorthand = dict()
    knownShorthand = sorts_independent_shorthand(independentShorthand, knownShorthand, syntaxFileName)
    previousShorthand = {}
    while dependentShorthand and dependentShorthand != previousShorthand:
        independentShorthand = {(role, term):shorthandLineNum for (role, term), shorthandLineNum in dependentShorthand.iteritems()
            if set(term.split()).intersection(shorthand) <= set(knownShorthand.keys())}
        previousShorthand = dependentShorthand
        dependentShorthand = {(role, term):shorthandLinenum for (role, term), shorthandLinenum in 
                dependentShorthand.iteritems() if not set(term.split()).intersection(shorthand) <= set(knownShorthand.keys())}
        for shorthand, sort in sorts_independent_shorthand(independentShorthand, knownShorthand, syntaxFileName).iteritems():
            assert not shorthand in knownShorthand, "Internal Error: It seems that our defMap is not a function like it's supposed to be: %s\n%s\n" % (
                    str(knownShorthand), str(shorthand))
            knownShorthand[shorthand] = sort
        newlyIndependentShorthand = sorts_independent_shorthand(independentShorthand, knownShorthand, syntaxFileName)
        for key, value in newlyIndependentShorthand.iteritems():
            assert key not in knownShorthand or knownShorthand[key] == value, "Internal Error: Disagreement on shorthand: %s\n%s\n%s\n" % (str(key), 
                    str(value), str(knownShorthand))
            knownShorthand[key] = value
    if dependentShorthand:
        raise pslErrors.TranslationError([pslErrors.error, pslErrors.color_line_number(', '.join([lineNum for (shorthand, lineNum) in 
            dependentShorthand])), "Shorthand dependencies cannot be resolved: ", ' '.join([' '.join([shorthand, ":=", term]) for
                ((role, term), (shorthand, lineNum)) in dependentShorthand.iteritems])])
    else:
        return knownShorthand

def sorts_independent_shorthand(independentShorthand, knownShorthand, syntaxFileName):
    """
    Given a mapping from (role, term) to (shorthand, lineNumber), and a mapping of all shorthand appearing in each "term" to their 
    respective
    sorts, returns a mapping of all shorthand in independentShorthand to their respective sorts.
    """
    maudeCmds = (["fmod SHORTHAND is", "protecting PROTOCOL-EXAMPLE-SYMBOLS ."] +
                [' '.join(['op', shorthand, ':', '->', sort, '.']) for (shorthand, sort) in knownShorthand.iteritems()] + 
                ["endfm"])
    maudeCmds += [' '.join(['parse', termRolePair[DEF_KEY_TERM], '.']) for termRolePair in independentShorthand.keys()] + ['q']
    maudeExecution = subprocess.Popen([MAUDE_COMMAND, NO_PRELUDE, '-no-banner', '-no-advise', '-no-wrap', PRELUDE, NPA_SYNTAX, 
        syntaxFileName], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = maudeExecution.communicate('\n'.join(maudeCmds))
    #Print any maude errors
    if stderr:
        stderr = stderr.strip().split('\n')
        errors = []
        for line in stderr:
            #Warning format:
            #Warning: <standard input>, line i: error message
            line = line.split(':')
            termIndex = int(line[1].split()[-1])
            startParsingIndex = maudeCmds.index('endfm')+2
            role, problemTerm = independentShorthand.keys()[termIndex - startParsingIndex]
            if "no parse for term" not in ''.join(line):
                errors.append(' '.join([pslErrors.error, 
                    pslErrors.color_line_number(independentShorthand[(role, problemTerm)][DEF_LINE_NUM]), 
                    "Term: ", pslErrors.color_token(problemTerm), ':'.join(line[2:])]))
        raise pslErrors.SyntaxError('\n'.join(errors))
    stdout = stdout.split('\n')
    stdout = [line.replace('Maude>', '').strip() for line in stdout]
    #Maude output after removing Maude>:
    #Sort: term
    return {independentShorthand[termRolePair][DEF_SHORTHAND]:line.split(':')[0] for termRolePair, line in 
            zip(independentShorthand, stdout)}

def is_function(defMap):
    """
    Given a mapping from pairs (role, term) |-> (shorthand, lineNum)
    checks to make sure that for any two
    (role, term) |-> (shorthand, lineNum)
    (role', term') |-> (shorthand', lineNum')

    term = term' iff shorthand = shorthand'

    In other words, the mapping from shorthand to 
    term defines a function.
    """
    definedShorthand = {}
    for role, term in defMap:
        shorthand, lineNumber = defMap[(role, term)]
        if shorthand in definedShorthand:
            tokenizedTerm1 = tokenize(term)
            term2, lineNumber2 = definedShorthand[shorthand]
            tokenizedTerm2 = tokenize(term2)
            if any([token1 != token2 for token1, token2 in zip(tokenizedTerm1, tokenizedTerm2)]):
                raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNumber) + ",",  pslErrors.color_line_number(lineNumber2),
                    "Multiple definitions of", pslErrors.color_token(shorthand)  + ":", pslErrors.color_token(term) + ",", pslErrors.color_token(term2)]))
        else:
            definedShorthand[shorthand] = (term, lineNumber)

def role_variables_correct(defMap, parseTree):
    """
    Given a mapping from pairs (role, term) |-> (shorthand, lineNum)
    checks to make sure that the variables in term are allowed
    to show up in terms associated with role. 
    """
    #Working on modifying the disjoint_vars code from pslTree.py to work here.
    protocol = parseTree.get_protocol()
    roleMap = protocol.variables_per_role()
    declaredVars = protocol.declared_variables()
    roleTermPairs = defMap.keys()
    errors = []
    checkedRoles = []
    for role, term in roleTermPairs:
        #checkedRoles.append(role)
        inVars = set(roleMap[role])
        otherStmtVars = protocol.statement_vars(float('inf'))
        otherStmtVars = {roleName:otherStmtVars[roleName] for roleName in otherStmtVars if roleName != role}
        #Because we've already passed the terms to Maude to be parsed, the variables in the term are annotated with their sort. We need to ignore that sort
        #when checking if a variable is in someone else's variables.
        for var in [token for token in tokenize(term) if token.split(':')[0] in declaredVars]:
            for roleName in otherStmtVars:
                varName = var.split(':')[0]
                if varName in otherStmtVars[roleName] and varName not in inVars:
                    errorMsg = ' '.join([pslErrors.error, pslErrors.color_line_number(defMap[(role, term)][LINE_NUM]), "Variable", pslErrors.color_token(varName.strip()), 
                        "appears in the protocol terms of roles",
                        pslErrors.color_token(roleName), "and", pslErrors.color_token(role) + ".",
                        "Variables must be disjoint between roles, with the possible exception of In(put) variables."])
                    if errorMsg not in errors:
                        errors.append(errorMsg)
    if errors:
        raise pslErrors.TranslationError('\n'.join(errors))



def parse_code(sectionStmts):
    root = pslTree.Root()
    try:
        root.children.append(pslTree.Theory.parse(sectionStmts['Theory'], root))
    except KeyError:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Theory")]))
    try:
        root.children.append(pslTree.Protocol.parse(sectionStmts['Protocol'], root))
    except KeyError:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Protocol")]))
    try:
        root.children.append(pslTree.Intruder.parse(sectionStmts['Intruder'], root))
    except KeyError:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Intruder")]))
    try:
        root.children.append(pslTree.Attacks.parse((sectionStmts['Attacks']), root))
    except KeyError:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Attacks")]))
    return root

SPEC_NAME = 1
def build_theory(parseTree, filePath, fileName):
    eqTheory = parseTree.get_theory()
    code = [line for line in eqTheory.translate() if line]
    syntax, equations = split_eq_theory(code)
    symbolsModuleName = "fmod PROTOCOL-EXAMPLE-SYMBOLS is protecting DEFINITION-PROTOCOL-RULES ."
    syntax.insert(0, symbolsModuleName)
    syntax.append('op _$;_ : Msg Msg -> Msg [ctor gather(e E) frozen].')
    syntax.append('endfm')
    equationModuleName = "fmod PROTOCOL-EXAMPLE-ALGEBRAIC is protecting PROTOCOL-EXAMPLE-SYMBOLS ."
    equations.insert(0, equationModuleName)
    equations.append('endfm')
    coherentEquations = make_coherent(equations, syntax)
    theoryFileName = os.path.join(filePath, '.'.join([fileName, 'maude']))
    with open(theoryFileName, 'w') as maudeFile:
        maudeFile.write('\n\n'.join(['\n'.join(syntax), '\n'.join(coherentEquations)]))
    return theoryFileName

def make_coherent(equations, syntax):
    """
    Given two iterables of lines (strings) of maude code, one representing PROTOCOL-EXAMPLE-ALGEBRAIC and the 
    other PROTOCOL-EXAMPLE-SYMBOLS,
    generates a new version of PROTOCOL-EXAMPLE-SYMBOLS where the equations have been made explicitly coherent modulo the axioms.
    """
    maudeExecution = subprocess.Popen([MAUDE_COMMAND, NO_PRELUDE, '-no-banner', '-no-advise', '-no-wrap', PRELUDE, NPA_SYNTAX],
         stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    maudeCode = syntax + equations
    maudeCode.append('load full-maude.maude .')
    maudeCode.append('( select AX-COHERENCE-COMPLETION .)')
    maudeCode.append(' '.join(['(', 'red axCohComplete(', 'upModule(', "'PROTOCOL-EXAMPLE-ALGEBRAIC,", 'false', ')', ')', '.)']))
    maudeCode.append('q')
    stdout, stderr = maudeExecution.communicate('\n'.join(maudeCode))
    if stderr:
        raise pslErrors.TranslationError(stderr)
    eqLines = [line for line in stdout.split('\n') if 'eq' in line.split()]
    equationModule = [line for line in equations if 'eq' not in line.split()]
    equationModule = equationModule[:-1] + compute_equations(eqLines, syntax) + [equationModule[-1]]
    return equations

def compute_equations(eqLines, syntax):
    """
    Given a list of strings, representing meta equations in Maude, and a list of lines representing the syntax file associated with
    the equations, returns a list of lines representing the Ax-complete object level
    Maude equations
    """
    maudeExecution = subprocess.Popen([MAUDE_COMMAND, NO_PRELUDE, '-no-banner', '-no-advise', '-no-wrap', PRELUDE, NPA_SYNTAX],
         stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    equationTerms = extract_equation_terms_attributes(eqLines)
    maudeCode = list(syntax)
    maudeCode.extend(["fmod THROW-AWAY is", "protecting PROTOCOL-EXAMPLE-SYMBOLS .", "protecting META-LEVEL .", 
        "op $$$m$$$ : -> [Msg] .",
        "endfm"])
    CONSTANT = "$$$m$$$"
    for left, right in equationTerms.items():
        right = right[0]
        maudeCode.append(' '.join(["red downTerm(", left, ",", CONSTANT, ")", "."]))
        maudeCode.append(' '.join(["red downTerm(", right, ",", CONSTANT, ")", "."]))
    maudeCode.append('q')
    stdout, stderr = maudeExecution.communicate('\n'.join(maudeCode))
    termList = [line[line.index(':')+1:].strip() for line in stdout.split('\n') if line.strip() and line.strip().split()[0] == 'result']
    termPairs = []
    leftTerm = True
    for term in termList:
        if leftTerm:
            termPairs.append([term])
            leftTerm = False
        else:
            leftTerm = True
            termPairs[-1].append(term)
    completeEqs = []
    for terms, attributes in zip(termPairs, equationTerms.values()):
        left, right = terms
        attributes = attributes[-1]
        completeEqs.append(' '.join(['eq', left, '=', right, '[', attributes, ']', '.']))
    return completeEqs


def extract_equation_terms_attributes(eqLines):
    """
    Given a list of strings representing maude meta-level equations eq metaTerm1= metaTerm2 [attributes], extracts and returns a dictionary
    {metaTerm1:(metaTerm2, attributes)}.
    """
    eqDict = {}
    for line in eqLines:
        lefthandSide, righthandSide = line.split('=')
        lefthandSide = lefthandSide.split()[1].strip()
        righthandSide, attributes = compute_righthand_attributes(righthandSide)
        attributes = attributes[:attributes.index(']')]
        eqDict[lefthandSide] = (righthandSide, attributes)
    return eqDict

def compute_righthand_attributes(righthandSide):
    """
    Given a righthand side of a meta equation, splits it into the righthand
    side of the equation, and the equation attributes, and returns them as
    an ordered pair.
    """
    righthandSide = righthandSide.strip()
    attributeStart = righthandSide.rfind('[')
    return (righthandSide[:attributeStart], righthandSide[attributeStart+1:-1])


def split_eq_theory(eqTheory):
    """
    Partitions the equational theory into the syntax and equations
    """
    spaceSplitTheory = [line.split() for line in eqTheory]
    equations = [' '.join(stmt) for stmt in spaceSplitTheory if stmt[0] == 'eq' or 
            stmt[0] == 'ceq'] 
    syntax = [stmt for stmt in eqTheory if stmt.split()[0] != 'eq' and stmt.split()[0] != 'ceq']
    return (syntax, equations)

if __name__ == '__main__':
    try:
        maudify()
    except pslErrors.PSLError, e:
        print(str(e))
