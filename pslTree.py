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
"""
Important: To simplify implementation, the parser assumes that the set of user-defined tokens are disjoint from the set of top level 
tokens.
"""
import re
import pslErrors
import itertools
import operator
import warnings
#from fuzzywuzzy import fuzz


TOP_LEVEL_TOKENS = ['sort', 'type', 'sorts', 'types', '.', 'subsort', 'subsorts', 'subtype', 'subtypes', 'op', 'ops', '->', ':', '[', ']', 'eq', '=', 'ceq', 'if', ':=', '==', 'In', '(', ')', 'Def', '(', ')',
        'Out', '=>', '<=>', ',', 'Intruder', 'learns', 'With', 'with', 'constraints:', 'without:', 'Subst', '|->', '!=', '|-', '$;']

'''
Blarge, don't really know what's going on with the bestTokenRatioPair crap, and I don't really feel like figuring it out right now.
def best_match(token, stmtTypes):
    """
    Takes a token, and a list of statement types (i.e. equational theory statements, intruder statements). Builds a list of tokens
    consisting of those tokens that begin each statement in stmtTypes, and returns the token that most closely matches the "token"
    argument.
    """
    bestTokenRatioPair = ('', 0)
    for stmtType in stmtTypes:
        startToken = stmtTypes[stmtType][0][0]
        ratio = fuzz.ratio(token, startToken)
        bestTokenRatioPair = (startToken, ratio) if ratio > bestTokenRatioPair[1] else bestTokenRatioPair
    tokens, args = (bestTokenRatioPair[0].tokens, iter(bestTokenRatioPair[0].argNodes))
    return ' '.join(next(args).class_name() if token == '_' else token for token in tokens)
'''


class Statement(object):
    """ 
    Contains a pair of lists. The first is a list of tokens, and the second is a list of line numbers, such that tokens[n] appears on 
    line lineNums[n]

    We could use a map, mapping tokens to line numbers, except that the same token may appear more than once in a single statement.
    """

    def __init__(self, tokens=None, lineNums=None):
        self.tokens = tokens if tokens else []
        self.lineNums = lineNums if lineNums else []
        #Yes, this check fails on strings, however I'm not treating strings as iterables, so this check should fail on
        #strings.
        assert(hasattr(self.tokens, '__iter__'))
        assert(hasattr(self.lineNums, '__iter__'))
        assert not (bool(self.tokens) ^ bool(self.lineNums)), "If 'tokens' is None (or empty), then 'lineNums' must also be None (or empty). If tokens is not None, then lineNums must also not be None."

    def __repr__(self):
        return str(zip(self.tokens, self.lineNums))
        """
        lines = []
        lineNums = []
        currentLine = []
        currentLineNum = self.lineNums[0]
        for token, lineNum in self:
            if lineNum == currentLineNum:
                currentLine.append(token)
            else: 
                lines.append(currentLine)
                lineNums.append(currentLineNum)
                currentLine = [token]
                currentLineNum = lineNum 
        lines.append(currentLine)
        lineNums.append(currentLineNum)
        lines = (' '.join(line) for line in lines)
        return '\n' + '\n'.join(map(' '.join, zip(["Line:"] * len(lineNums), map(str, lineNums), lines)))
        """

    def append(self, value, lineNum):
        self.tokens.append(value)
        self.lineNums.append(lineNum)


class Node(object):
    """
    Represents a Node in the AST. Consists of:
    1. The operator of the associated statement.
    2. Children nodes consisting of arguments to the 
        high-level argument.
    3. The line at which this node occurs in the 
        original file.

    For example, a statement of the form
    1 . A -> B : pk(A, B) |- M .  on line 5 would have a 
    Node that looks like:
    
    Node(_._->_:_|-_., 
        Node(1, [], 5), 
        Node(A, [], 5), 
        Node(B, [], 5), 
        Node(pk(A, B), [], 5), 
        Node(M, [], 5), 5)

    Note that we don't attempt to parse user-defined
    operators. We leave that to Maude.

    Also has a function associated with it that performs error checking
    for this particular node.
    """
    def __init__(self, parent=None, op=None, children=None, lineNum=None):
        """
        op is a tuple of tokens representing the syntax of the statement describing this Node. children is an iterable of Nodes (or strings if we're at a leaf node, i.e. a Token) below this Node in the Tree, and line is the line number at which the Node's 
        statement begins.
        """
        self.op = op
        self.parent = parent
        if children is None:
            children = []
        self.children = children 
        self.lineNum = lineNum

    def error_check(self):
        raise NotImplementedError(self.class_name())

    def get_ops(self):
        return self.parent.get_ops()

    def get_root(self):
        root = self
        while root.parent:
            root = root.parent
        return root

    def translate(self):
        """
        Returns an iterable of lines of Maude code that translates the information contained in this Node into Maude-NPA code.
        """
        code = []
        assert self.children, "Node %s doesn't have any children. Perhaps you forgot to implement a custom translate() method for this node?" % str(self)
        for child in self.children:
            code.extend(child.translate())
        return code

    @staticmethod
    def parse(stmt, parent):
        """
        Given an object with the statement interface (an iterable of strings representing tokens, and an iterable of numbers representing line numbers on which those tokens appear), attempts to parse the statement
        into a parse tree. If successful, returns a parse tree with 
        this node at the root. Otherwise, raises a SyntaxError.

        This is the function that should be overriden by children classes. The _parse static method is an internal method meant to be invoked by the children Nodes, because most of them perform the same basic
        algorithm. _parse implements that algorithm.
        """
        pass

    def _parse(self, stmt, syntax):
        """
        Given an object with the statement interface (an iterable of strings representing tokens, and an iterable of numbers representing 
        line numbers on which those tokens appear), attempts to parse the statement
        into a parse tree. If successful, returns a parse tree with 
        this node at the root. Otherwise, raises a SyntaxError.

        This method is meant to be invoked by the child classes of Node

        Observe that at this level, we don't know what type of node to return. So this parse function simply returns a triple of the 
        operator tuple associated with the calling node, the arguments of the calling node, and the starting Line number. 
        The calling node then uses that information to construct a node of the appropriate type.
        """
        tokens = stmt.tokens
        opIter, argNodes = (iter(syntax.tokens), iter(syntax.argNodes))
        args = []
        unparsedTokens = iter(tokens)
        lineNumIter = iter(stmt.lineNums)
        startingLineNum = None
        terminatingToken = None
        userLevelTokenList = []
        userLevelLineNums = []
        for token in opIter:
            if token == '_':
                userLevelTokenList = []
                userLevelLineNums = []
                #Some syntaxes (i.e. DefPair) have an _ as the last token in the syntax.
                try:
                    terminatingToken = next(opIter)
                except StopIteration:
                    terminatingToken = None
                stmtToken = next(unparsedTokens)
                while stmtToken != terminatingToken:
                    userLevelTokenList.append(stmtToken)
                    currentLine = next(lineNumIter)
                    if startingLineNum is None:
                        startingLineNum = currentLine
                    userLevelLineNums.append(currentLine)
                    try:
                        stmtToken = next(unparsedTokens)
                    except StopIteration:
                        if terminatingToken:
                            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(currentLine), "Missing",
                                pslErrors.color_token(terminatingToken), "in line: ", ' '.join(color_stmt_tokens(stmt.tokens)), 
                                "Expected a statement of the form: ", ' '.join(color_stmt_tokens(syntax.tokens))]))
                        else:
                            break
                args.append(next(argNodes).parse(Statement(userLevelTokenList, userLevelLineNums), self))
            else:
                try:
                    unparsedToken = next(unparsedTokens)
                except StopIteration:
                    #This check may (or may not, I'm not sure) vary depending on the statement.
                    if token == '.':
                        break
                    else:
                        raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(currentLine), "Missing a token matching: ",
                            pslErrors.color_token(token), "When parsing line: ", pslErrors.color_token(' '.join(stmt.tokens)), 
                            "Expected a", "statement of the form: ", pslErrors.color_token(' '.join(syntax.tokens))]))
                else:
                    currentLine = next(lineNumIter)
                    if startingLineNum is None:
                        startingLineNum = currentLine
                    if token != unparsedToken:
                        raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(currentLine), "Unexpected token:", 
                            pslErrors.color_token(unparsedToken), "when parsing statement:", pslErrors.color_token(' '.join(stmt.tokens)), 
                            "Expected statement of the form: ", pslErrors.color_token(' '.join(syntax.tokens))]))
        return (syntax.tokens, args, startingLineNum)

    def __repr__(self):
        return '\n'.join(['$$$$$$$$', 'Op::', repr(self.op), 'Line Number::', repr(self.lineNum), 'Children::', '----------------\n'.join(map(repr, self.children)), '########'])

    @staticmethod
    def class_name():
        return "Node"



class Root(Node):

    def __init__(self, op=None, children=None, lineNum=None):
        super(Root, self).__init__(None, op, children, lineNum)

    @staticmethod
    def class_name():
        return "Root"
    
    def get_theory(self):
        try:
            return next(child for child in self.children if child.class_name() == Theory.className)
        except StopIteration:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Theory")]))

    def get_protocol(self):
        try:
            return next(child for child in self.children if child.class_name() == Protocol.className)
        except StopIteration:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Protocol")]))

    def get_intruder(self):
        try:
            return next(child for child in self.children if child.class_name() == Intruder.className)
        except StopIteration:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Intruder")]))

    def get_attacks(self):
        try:
            return next(child for child in self.children if child.class_name() == Attacks.className)
        except StopIteration:
            raise pslErrors.SyntaxError(' '.join([pslErrors.errorNoLine, "Missing Section:", pslErrors.color_token("Attacks")]))

    def sort_names(self):
        return self.get_theory().sort_names()

    def get_ops(self):
        ops = []
        for child in self.children:
            try:
                ops.append(child.get_user_defined_operator())
            except AttributeError:
                pass
        return ops


class Section(Node):

    def declared_variables(self, upToNode=None):
        """
        upToNode is a VarDeclNode. If upToNode is not None, then Theory will return all the variables declared before upToNode. This is 
        particularly useful when checking for duplicate variable declarations.

        Note: This returns only the variable NAMES. It does not return the sorts of the variables.
        """
        declaredVars = []
        for child in self.children:
            if child is upToNode:
                break
            try:
                declaredVars.extend(child.get_vars()) 
            except AttributeError:
                pass
        return declaredVars

    def var_name_sort_mapping(self):
        """
        Returns a map from variable name to the variable's sort for all variables declared in this section.
        """
        declaredVars = {}
        for child in self.children:
            try:
                childMapping = child.name_sort_mapping()
            except AttributeError:
                pass
            else:
                for varName in childMapping:
                    declaredVars[varName] = childMapping[varName]
        return declaredVars


class PSLSection(Section):

    def sort_names(self):
        return self.parent.sort_names()

    def translate(self):
        self.error_check()
        return [self.class_name(), '{'] + super(PSLSection, self).translate() + ['}']


class Theory(Section):
    """
    Root of the theory syntax tree.
    Note that the theory section behaves differently from the other sections in a variety of ways, so it is not made a subtype of PSLSection, but rather only of Section
    """
    
    className = "Theory"

    def __init__(self, parent, line=0):
        super(Theory, self).__init__(parent, None, [], line)

    def class_name(self):
        return Theory.className

    def sort_nodes(self):
        """
        Returns the list of nodes that declare sort names.
        """
        return [arg for arg in self.children if arg.op in typeSyntax]

    def sort_names(self):
        """
        Returns a list of sort names declared in this module.
        """
        sortNames = []
        for arg in self.children:
            try:
                sortNames.extend(arg.sort_names())
            except AttributeError:
                pass
        return sortNames

    def ops(self):
        ops = []
        for child in self.children:
            try:
                ops.append(child.get_user_defined_operator())
            except AttributeError:
                pass
        return ops

    @staticmethod
    def parse(stmts, parent):
        #stmts is a list of Statement objects, each of which consists of a list of tokens and an associated list of line numbers for 
        #each token.
        root = Theory(parent)
        keywordList = [['type', 'sort', 'types', 'sorts'], ['subtype', 'subtypes', 'subsort', 'subsorts'], ['op', 'ops'],
                ['var', 'vars'], ['eq', 'ceq']]
        syntaxDeclPairs = [(typeSyntax, TypeDecl), (subTypeSyntax, SubTypeDecl), (opSyntax, OpDecl), (varSyntax, VarDecl), 
                (eqSyntax, EqStmt)]
        stmtTypes = {}
        #These are already in PROTOCOL-DEFINITION-RULES, so we don't need to add them explicitly. We do however, need to remove them
        #if people already declared them.
        #builtInSorts = ['sorts'] + TypeDecl.builtInTypes + ['.']
        #stmts = [Statement(builtInSorts, [-1] * len(builtInSorts))] + stmts
        for keywords, sdPair in zip(keywordList, syntaxDeclPairs):
            for word in keywords:
                stmtTypes[word] = sdPair
        for stmt in stmts:
            for stmtType in stmtTypes:
                syntaxList, nodeType = stmtTypes[stmtType]
                if any(stmt.tokens[0] == stmtSyntax.tokens[0] for stmtSyntax in syntaxList):
                    root.children.append(nodeType.parse(stmt, root))
                    break
            else:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Token", 
                    pslErrors.color_token(stmt.tokens[0]), "does not begin an equational theory statement."])) #Did you mean:", 
                    #pslErrors.color_token(best_match(stmt.tokens[0], stmtTypes)) + '?']))
        #Make all sorts subsorts of Msg.
        subsortDecl = ['subsorts'] + [sortName for sortName in root.sort_names() if sortName != 'Msg'] + ['<', 'Msg', '.']
        root.children.append(SubTypeDecl.parse(Statement(subsortDecl, [-1] * len(subsortDecl)), root))
        assert all(root.children)   
        return root

    def error_check(self): 
        """
        If performance becomes an issue (unlikely considering the very small
        size of specifications compared to programs. I doubt a specification
        is going to be millions of lines of code!) then we can check for
        duplicates as we parse the sort names
        """
        errors = []
        warnings = []
        for arg in self.children:
            try:
                arg.error_check()
            except pslErrors.PSLError, e:
                errors.append(e)
            except pslErrors.PSLWarning, e:
                warnings.append(e)
        try:
            self.check_repeated_sorts()
        except pslErrors.SyntaxWarning, e:
            warnings.append(e)
        try:
            self.check_axioms()
        except pslErrors.InvalidOpError, e:
            errors.append(e)
        if errors or warnings:
            raise pslErrors.ErrorsAndWarnings(errors + warnings, errors, 
                    warnings)

    def check_repeated_sorts(self):
        """
        Checks if the theory section has any multiply declared sorts. If 
        there are any, then the program raises a SyntaxWarning.
        """
        seenSorts = set()
        errorMsgs = []
        for node in self.sort_nodes():
            for sort in node.sort_names():
                if sort in seenSorts:
                    errorMsgs.append(' '.join([pslErrors.warning, 
                        pslErrors.color_line_number(node.line), "Sort", 
                        pslErrors.color_token(sort), "already declared, and will be",
                        "ignored."]))
                    node.remove_sort(sort)
                else:
                    seenSorts.add(sort)
        if errorMsgs:
            raise pslErrors.SyntaxWarning('\n'.join(errorMsgs))

    def check_axioms(self):
        """
        Checks to make sure the theory has only allowed combinations of axioms: 
        assoc-comm, comm, assoc-comm-id.
        assoc, assoc-id, any combination containing only left-id, any 
        combination containing right-id, or any combination containing idem are 
        not allowed.
        """
        #TODO: Implement
        ops = self.get_op_nodes()

    def get_op_nodes(self):
        return [arg for arg in self.children if arg.op in opSyntax]


class StmtNode(Node):
    """
    A StmtNode (statement node) is a node that a single Maude-NPA statement (i.e. a sort declaration, an operator, an equation).
    It is assumed that Statement nodes contain a tuple "op" that defines their syntax. For example ('op', '_', ':', '_', '->', '_', '.') represents an op statement without brackets, where
    underscores represent the position at which the user provides input. Furthermore the ith _ should correspond to the ith child of this node.
    """

    @staticmethod
    def class_name():
        return "StmtNode"

    def translate(self):
        self.error_check()
        code = list(self.op)
        underscoreIndices = [i for i, x in enumerate(self.op) if x == '_']
        for i in range(len(self.children)):
            code[underscoreIndices[i]] = ' '.join(''.join(child) for child in self.children[i].translate())
        return [' '.join(code)]


class PSLStmtNode(StmtNode):

    className = "PSL Statement Node"
   
    def class_name(self):
        return PSLStmtNode.className
        

    def translate(self):
        """
        If we're translating statements that are not in the theory section, then we need to append the line number onto the end.
        """
        code = super(PSLStmtNode, self).translate()
        #Since these are all single statements, they should only create a single line of Maude code.
        assert len(code) == 1
        return self.append_line_number(code)

    def append_line_number(self, code):
        code = code[0]
        return [' '.join([code, '[', str(self.lineNum), ']'])]


class TypeDecl(StmtNode):
    """
    Used to encode type declarations (i.e. statements prefixed by one of:
    sort(s), type(s)
    A TypeDecl's children is a single PSLListNode of Tokens containing the sort names.
    """

    builtInTypes = ['Msg', 'Public', 'Fresh']

    @staticmethod
    def class_name():
        return "Type Declaration"

    @staticmethod
    def parse(stmt, parent):
        syntax = next(syntax for syntax in typeSyntax if stmt.tokens[0] == syntax.tokens[0])
        node = TypeDecl(parent, None, None, None) 
        op, children, lineNum = node._parse(stmt, syntax)
        node.op = op
        node.children = children
        node.lineNum = lineNum
        assert all(node.children)
        return node

    def sort_names(self):
        """
        Returns a list of sort names declared in this node.
        """
        sortList = []
        for child in self.children:
            sortList.extend(child.get_elements())
        return [elem.get_token() for elem in sortList]

    def remove_sort(self, sort):
        for child in self.children:
            try:
                self.children.remove(sort)
            except ValueError:
                pass
            else:
                break

    def add_sort(self, sort):
        self.children[0].children.append(sort)

    def translate(self):
        self.op[0] = 'sorts'
        return super(TypeDecl, self).translate()

    def error_check(self):
        errorMsgs = []
        for sortName in self.sort_names():
            invalidTokenMsg = self.invalid_tokens(sortName)
            if invalidTokenMsg: 
                errorMsgs.append(invalidTokenMsg)
            if sortName in TypeDecl.builtInTypes:
                errorMsgs.append(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), 
                    "Type", pslErrors.color_token(sortName),
                    "already has a special meaning in Maude-NPA, and should not be explicitly declared in a PSL specification."]))
        if errorMsgs:
            raise pslErrors.SyntaxError('\n'.join(errorMsgs))

    def invalid_tokens(self, sortName):
        invalidTokens = ['`', '}', '{', '(', ')', '[', ']', ',']
        invalidTokens = ', '.join([token for token in invalidTokens if token in sortName])
        if invalidTokens:
            return ' '.join(["Invalid tokens:", pslErrors.color_token(invalidTokens),
                    "are not allowed in sort names.", 
                    "Invalid sort name: ", pslErrors.color_token(sortName)])
        else:
            return ''


class Term(Node):
    """
    Used for discrete units of syntax (i.e. individual terms that serve 
    as arguments to one of the statements listed at bottom of this
    file). These include
    variables, numbers and terms using user-defined syntax that Python can't
    handle as well as Maude.
    """

    @staticmethod
    def class_name():
        return "Term"

    def __init__(self, parent=None, children=None, lineNum=None):     
        """
        Children is an iterable of Tokens. lineNum is the line number on which this term begins.
        op is not specified by the creator. It is always '_' because terms should only appear in 
        places where '_' appears in the high level syntax.
        """
        super(Term, self).__init__(parent, '_', children, lineNum)

    def __repr__(self):
        return '\n'.join(map(repr, self.children))

    def __str__(self):
        return ' '.join(map(str, self.children))

    def tokens(self):
        return self.children

    @staticmethod
    def parse(stmt, parent):
        node = Term(parent, [], stmt.lineNums[0])
        node.children = [Token(node, [token], lineNum) for token, lineNum in zip(stmt.tokens, stmt.lineNums)]
        return node

    def translate(self):
        code = []
        opDecls = self.parent.get_ops()
        for child in self.children:
            code.extend(child.translate())
        return [' '.join(code)]

    def get_tokens(self):
        """
        Returns the tokens (as token objects) that make up this term.
        """
        return self.children


class Token(Node):
    """
        A single token. This is a leaf node of the parse tree.
    """
                              #start multi-line comment /* ... */|end multi-line comment 
                              #| single line comment|start of specification| parens/brackets/curly braces | whitespace
    #tokenizer = re.compile(r'(/\*)|(\*/)|(//.*$)|(spec \S+ is)|([[\](){}])|(,)|(_)|(\s)')
    tokenizer = re.compile(r'(/\*)|(\*/)|(//.*$)|(spec \S+ is)|([[\](){}])|(,)|\s')

    @staticmethod
    def class_name():
        return "Token"

    def __init__(self, parent, tokenList, lineNum):
        assert(isinstance(tokenList, list))
        super(Token, self).__init__(parent, None, tokenList, lineNum)

    @staticmethod
    def parse(stmt, parent, lineNum=None):
        assert len(stmt.tokens) == 1, "Statement has been passed to the Token node with more than one tokens: %s" % ', '.join(stmt.tokens)
        assert len(stmt.lineNums) == 1, "Statement has been passed to the Token node with more than one line number: %s" % ', '.join(map(str, stmt.lineNums))
        return Token(parent, stmt.tokens, stmt.lineNums)

    def get_token(self):
        return self.children[0]

    def translate(self):
        """
        We don't need to do anything fancy to tokens to turn them into Maude-NPA code, since they're just discrete bits of string that are provided by the user.
        """ 
        token = self.get_token()
        parent = self.parent
        while True:
            try:
                declaredVars = parent.declared_variables()
            except AttributeError:
                parent = parent.parent
            else:
                break
        if token in declaredVars:
            parent = self.parent
            while True:
                try:
                    varsWithSorts = parent.var_name_sort_mapping()
                except AttributeError:
                    parent = parent.parent
                else:
                    break
            token = ':'.join([token, varsWithSorts[token]])
        return [token]

    def __repr__(self):
        return ''.join([str(self.lineNum), ': ', ''.join(self.children)])

    def __str__(self):
        return ''.join(self.children)


class SubTypeDecl(StmtNode):
    """
    The child of a SubTypeDecl node is a PSLListNode of lists of tokens: [[Token_1, Token_2, ..., Token_n], ..., [Token_m1, Token_m2, ... Token_mp] s.t. 
     s.t. Token_1 Token_2 ... Token_n < ... < Token_m1 Token_m2 ... Token_mp 
    """

    @staticmethod
    def class_name():
        return "Subtype Declaration"

    @staticmethod
    def parse(stmt, parent):
        syntax = next(syntax for syntax in subTypeSyntax if syntax.tokens[0] == stmt.tokens[0])
        node = SubTypeDecl(parent, None, None, None)
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        assert all(node.children)
        return node

    def translate(self):
        self.op[0] = 'subsorts'
        code = super(SubTypeDecl, self).translate()[0]
        return [code]

    def error_check(self):
        """
        All we need to check for subtype declarations is that the sorts used in the sub type declaration have been declared.
        """
        declaredSorts = self.parent.sort_names()
        sortNames = []
        for child in self.children:
            assert not isinstance(child.get_elements(), Node), "Should be a list: %s" % str(child.get_elements)
            for element in child.get_elements():
                sortNames.extend(element.get_elements())
        sortNames = [sort.get_token() for sort in sortNames]
        undeclaredSorts = [sort for sort in sortNames if not sort in declaredSorts]
        errorMsgs = ''
        for sort in filter(lambda x : x not in TypeDecl.builtInTypes, undeclaredSorts):
            '\n'.join([errorMsgs, ' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Type name: ", pslErrors.color_token(sort) + " has not been declared."])])
        if errorMsgs:
            raise pslErrors.SyntaxError(errorMsgs)

class OpDecl(StmtNode):

    @staticmethod
    def class_name():
        return "Op Declaration"

    @staticmethod
    def parse(stmt, parent):
        #First, we distinguish between op and ops, then we'll distinguish between [_] and no [_].
        syntaxList = [syntax for syntax in opSyntax if stmt.tokens[0] == syntax.tokens[0]]
        reversedTokens = stmt.tokens[::-1]
        indexBeforeColon = reversedTokens.index(':')-1
        if stmt.tokens[-2] == ']':
            syntaxList = (syntax for syntax in syntaxList if syntax.tokens[-2] == ']')
        else:
            syntaxList = (syntax for syntax in syntaxList if syntax.tokens[-2] != ']')
        #We're checking the token after the colon in the original, non-reversed list.
        if reversedTokens[indexBeforeColon] == '->': 
            syntax = next(syntax for syntax in syntaxList if syntax.tokens[-syntax.tokens[::-1].index(':')] == '->')
        else:
            syntax = next(syntax for syntax in syntaxList if syntax.tokens[-syntax.tokens[::-1].index(':')] != '->')
        node = OpDecl(parent, None, None, None)
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        assert all(node.children)
        return node

    def translate(self):
        #Need to check if one of the attributes is frozen.
        if '[' in self.op:
            attributes = self.get_attributes()
            if not 'frozen' in attributes and not self.is_constant():
                opAttributeList = self.children[-1] 
                opAttributeList.append(Token(self, ['frozen'], self.lineNum))
            elif not self.is_constant():
                frozenIndex = attributes.index('frozen')
                #This handles converting frozen(1, 2, 3) (or whatever operator positions) into frozen, since Maude-NPA requires every 
                #argument to be frozen.
                try:
                    startParenIndex = frozenIndex+1
                except IndexError:
                    pass
                else:
                    try:
                        endParenIndex = attributes[frozenIndex:].index(')')
                    except ValueError:
                        raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), 
                            "Unbalanced parenthesis when declaring frozen properties."]))
                    self.children[-1].remove_range(startParenIndex, endParenIndex)
                    warnings.warn(' '.join([pslErrors.warning, pslErrors.color_line_number(self.lineNum), 
                        "Maude-NPA requires all arguments on all operators to be frozen. Your partially frozen operator",
                        "has been converted into a completely frozen operator."]))
        else:
            if not self.is_constant():
                self.children.append(PSLListNode(self, '', [Token(self, ['frozen'], self.lineNum)], self.lineNum))
                #Need to change the op to be the version with operator attributes. Note that since we don't add frozen to the constant 
                #operators, we don't care about 
                #changing those (because we don't need to).
                if 'ops' in self.op:
                    self.op = opSyntax[-1].tokens
                else:
                    self.op = opSyntax[1].tokens
        return super(OpDecl, self).translate()

    def is_constant(self):
        userOp = self.op[self.op.index(':'):self.op.index('->')]
        for token in userOp:
            if '_' in token:
                return False
        else:
            return True

    def error_check(self):
        attributes = self.get_attributes()
        if 'assoc' in attributes and not 'comm' in attributes:
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Operator attribute", pslErrors.color_token('assoc'), "not allowed without the",
                pslErrors.color_token('comm'), "attribute"]))
        if 'id:' in attributes and not ('assoc' in attributes and 'comm' in attributes):
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Operator attribute", pslErrors.color_token('id:'), "not allowed without the",
                pslErrors.color_token('comm'), "and", pslErrors.color_token('assoc'), "attributes."]))
        if 'idem' in attributes:
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Operator attribute", pslErrors.color_token('idem'), "is not allowed."]))
        userDefinedOperator = self.get_user_defined_operator()
        for token in userDefinedOperator:
            if token in TOP_LEVEL_TOKENS and (token != '(' and token != ')' or token == 'op'):
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Token:", pslErrors.color_token(token), 
                    "is a token in the Maude-PSL top level syntax",
                    "and therefore is not allowed in a user-defined operator. Consider doubling the token (i.e.", pslErrors.color_token(token + token), "or tweaking the token in some other manner",
                    "to make it distinct."]))
            elif (token == '(' or token == ')') and token == 'ops':
                warnings.warn(' '.join([pslErrors.warning, pslErrors.color_line_number(self.lineNum), "Token ", 
                    pslErrors.color_token(token),
                    "is not allowed to be part of a user-defined operator. Therefore,", pslErrors.color_token(token), 
                    "is assumed to be enclosing one of several operators declared on the same line."])) 

    def get_attributes(self):
        if '[' in self.op:
            opAttributes = self.children[-1]
            return [attribute.get_token() for attribute in opAttributes.children]
        else:
            return []

    def get_user_defined_operator(self):
        return [elem.get_token() for elem in self.children[0].get_elements()]


class VarDecl(StmtNode):

    className = "Variable Declaration"

    @staticmethod
    def class_name():
        return "Variable Declaration"

    @staticmethod
    def parse(stmt, parent):
        syntax = next(syntax for syntax in varSyntax if stmt.tokens[0] == syntax.tokens[0])
        node = VarDecl(parent, None, None, None)
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        assert all(node.children)
        return node

    def get_sort_name(self):
        return self.children[1].get_token()

    def get_vars(self):
        """
        Returns the tokens that represent variable names declared as a part of this decl.
        """
        return [elem.get_token() for elem in self.children[0].get_elements()]

    def error_check(self):
        varNames = self.get_vars()
        allVarsUpToMe = self.parent.declared_variables(self)
        redeclaredVars = [varName for varName in varNames if varName in allVarsUpToMe]
        if redeclaredVars:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Variables: ", 
                pslErrors.color_token(' '.join(redeclaredVars)), "have already been declared."]))
        if not self.get_sort_name() in self.parent.sort_names() + TypeDecl.builtInTypes:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Sort: ", 
                pslErrors.color_token(self.get_sort_name()), "has not been declared."]))

    def name_sort_mapping(self):
        """
        Returns a mapping from var name to sort name for each var name in this var declaration.
        """
        sortName = self.get_sort_name()
        return {varName:sortName for varName in self.get_vars()}

    def translate(self):
        """
        We convert all the variables into inline declarations as part of the translation of the Tokens, so we don't carry over the explicit variable declarations into the Maude code.
        """
        self.error_check()
        return ['']

        
class EqStmt(StmtNode):

    @staticmethod
    def class_name():
        return "Equation"

    @staticmethod
    def parse(stmt, parent):
        if stmt.tokens[-2] == ']':
            syntax = next(syntax for syntax in eqSyntax if syntax.tokens[-2] == ']')
        else:
            syntax = next(syntax for syntax in eqSyntax if syntax.tokens[-2] != ']')
        node = EqStmt(parent, None, None, None)
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        assert all(node.children), "%s" % str(node)
        return node

    def get_attributes(self):
        if '[' in self.op:
            attributes = [elem.get_token() for elem in self.children[-1].get_elements()]
            return attributes
        else:
            return []

    def translate(self):
        self.error_check()
        if '[' in self.op:
            attributes = self.get_attributes()
            if not 'variant' in attributes and not 'homomorphism' in attributes:
                self.children[-1].append(Token(self, ['variant'], self.lineNum))
            elif 'homomorphism' in attributes:
                self.children[-1].remove('homomorphism')
                newTokens = ['label', 'homomorphism', 'metadata', '"builtin-unify"']
                self.children[-1].extend([Token(self, [token], self.lineNum) for token in newTokens])
            if not 'nonexec' in attributes:
                pass
                #self.children[-1].append(Token(self, ['nonexec'], self.lineNum))
        else:
            self.op = eqSyntax[1].tokens
            self.children.append(PSLListNode(self, '', [Token(self, ['variant'], self.lineNum)],  self.lineNum))
                #Token(self, ['nonexec'], self.lineNum)]
        return super(EqStmt, self).translate()

    def error_check(self):
        attributes = self.get_attributes()
        if '[' in self.op:
            if 'variant' in attributes and 'homomorphism' in attributes:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), 
                    "Equation cannot have both the attribute:", pslErrors.color_token('variant'), 'and the attribute:', 
                    pslErrors.color_token('homomorphism') + '.']))



class Int(Node):
    """
    Encapsulates integers
    """

    @staticmethod
    def class_name():
        return "Integer"

    @staticmethod
    def parse(stmt, parent):
        if len(stmt.tokens) != 1:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Expected a single integer when parsing ", pslErrors.color_token(' '.join(stmt.tokens)) + ".", "Make sure there are no spaces between your digits, and there is a",
            "period after the integer."]))
        try:
            int(stmt.tokens[0])
        except ValueError:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Expected: ", pslErrors.color_token(' '.join(stmt.tokens)), "to be an integer."]))
        else:
            return Int(parent=parent, children=stmt.tokens, lineNum=stmt.lineNums[0])

    def translate(self):
        return [self.children[0]]

    def value(self):
        return int(self.children[0])


class Protocol(PSLSection):

    className = "Protocol"

    @staticmethod
    def class_name():
        return Protocol.className

    def role_names(self):
        roleNames = []
        for child in self.children:
            try:
                roleNames.extend(child.role_names())
            except AttributeError:
                pass
        return roleNames

    def role_decls(self):
        roleDecls = []
        for child in self.children:
            if child.className == RoleDecl.className:
                roleDecls.append(child)
        return roleDecls

                
    def __init__(self, parent, line=0):
        super(Protocol, self).__init__(parent, None, [], line)

    def statement_vars(self, stepNumber):
        """
        Returns a mapping from role names (as strings) to the variables that appear in that role's protocol steps and input (as strings).
        """
        allStepVars = {}
        for child in self.children:
            try:
                childStepNumber = child.get_step_number()
            except AttributeError:
                pass
            else:
                if childStepNumber <= stepNumber:
                    stepVars = child.statement_vars()
                    for role in stepVars:
                        if role in allStepVars:
                            allStepVars[role].extend(stepVars[role])
                        else:
                            allStepVars[role] = stepVars[role]
        return allStepVars 

    def variables_per_role(self):
        """
        Returns a map, mapping role names to a list of variables that may show up in that role's terms.
        """
        return {inDecl.role_name():inDecl.variables() for inDecl in self.in_decls()}

    def in_decls(self, upToMe=None):
        inDecls = []
        for child in self.children:
            if child is upToMe:
                break
            elif child.class_name() == InDecl.className:
                inDecls.append(child)
        return inDecls

    def in_decl_with_role_name(self, roleName):
        return next(inDecl for inDecl in self.in_decls() if inDecl.role_name() == roleName)

    def out_decls(self):
        return [child for child in self.children if child.class_name() == OutDecl.className]

    def in_decl_role_names(self, upToMe=None):
        return [inDecl.role_name() for inDecl in self.in_decls(upToMe)]

    def out_decl_role_names(self):
        return [outDecl.role_name() for outDecl in self.out_decls()]

    def get_defs(self):
        return [child for child in self.children if child.class_name() == DefDecl.className]

    @staticmethod
    def parse(stmts, parent):
        root = Protocol(parent)
        #Possible beginnings of each statement:
        #1. roles
        #2. Def
        #3. In
        #4. Out
        #5. An integer
        #6. var(s)
        stmtTypes = [roleSyntax, defSyntax, outSyntax, inSyntax, varSyntax[0], varSyntax[1]]
        for stmt in stmts:
            for stmtType in stmtTypes:
                if stmt.tokens[0] == stmtType.tokens[0]:
                    root.children.append(stmtType.stmtNode.parse(stmt, root))
                    break
            else:
                try:
                    int(stmt.tokens[0])
                except ValueError:
                    raise SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Token", 
                        pslErrors.color_token(stmt.tokens[0]), "does not begin a Protocol statement."]))
                else:
                    root.children.append(stepSyntax.stmtNode.parse(stmt, root))
        return root

    def error_check(self): 
        roleDecls = self.role_decls()
        inDeclRoleNames = set(self.in_decl_role_names())
        outDeclRoleNames = set(self.out_decl_role_names())
        for roleDecl in roleDecls:
            roleNames = roleDecl.role_names()
            for role in roleNames:
                if role not in inDeclRoleNames:
                    raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(roleDecl.lineNum), 
                        "Missing In(put) for role", pslErrors.color_token(role) + ".", 
                        ' '.join(["The roles syntax does NOT contain a colon." if role == ':' else "The role names are NOT separated by commas. They are separated by spaces.", 
                            "Role Syntax:", pslErrors.color_token(' '.join(['roles', 'Role1', 'Role2', 'Role3', '.']))]) if role == ':' or role == ',' else ''
                        ]))
                if role not in outDeclRoleNames:
                    raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(roleDecl.lineNum), 
                        "Missing Out(put) for", pslErrors.color_token(role) + "."]))

class RoleDecl(PSLStmtNode):

    className = "Role Declaration"

    def class_name(self):
        return RoleDecl.className

    def role_names(self):
        return [role.role_name() for role in self.roles()]

    def roles(self):
        roles = []
        for child in self.children:
            roles.extend(child.get_elements())
        return roles

    @staticmethod
    def parse(stmt, parent):
        node = RoleDecl(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, roleSyntax)
        return node

    def error_check(self):
        pass

    def translate(self):
        """
        Roles do not show up in the Maude code. They're only used to catch errors at the PSL level.
        """
        return []


class Role(Node):

    def class_name(self):
        return "Role"

    @staticmethod
    def parse(stmt, parent):
        node = Role(parent=parent)
        assert len(stmt.tokens) == 1, "Role: %s" % str(stmt.tokens)
        node.children = stmt.tokens
        node.lineNum = stmt.lineNums[0]
        return node

    def role_name(self):
        return self.children[0]

    def translate(self):
        self.error_check()
        return [self.children[0] + ':Role']

    def error_check(self):
        roleNames = self.get_root().get_protocol().role_names()
        if self.role_name() not in roleNames:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Undeclared role:", 
                pslErrors.color_token(self.role_name()) + ".", "Declared role names:", 
                pslErrors.color_token(', '.join(roleNames) if roleNames else "None")]))


class TermList(Node):

    @staticmethod
    def parse(stmt, parent):
        """
        Because of the difficulty in parsing terms in a comma-separated list, we punt that parsing off to Maude.
        """
        node = TermList(parent)
        node.children = [Token(node, [token], lineNum) for token, lineNum in zip(stmt.tokens, stmt.lineNums)]
        node.lineNum = stmt.lineNums[0]
        return node

    def translate(self):
        return [child.translate() for child in self.children]


class InDecl(PSLStmtNode):

    className = "In Declaration"

    def class_name(self):
        return InDecl.className

    @staticmethod    
    def parse(stmt, parent):
        node = InDecl(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, inSyntax)
        return node

    def error_check(self):
        if self.children[0].role_name() not in self.parent.role_names():
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Undeclared role name:", pslErrors.color_token(self.children[0].role_name())]))
        if self.children[0].role_name() in self.parent.in_decl_role_names(self):
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Input for role", pslErrors.color_token(self.children[0].role_names()), 
                "already declared", "on line: ", pslErrors.color_line_number(self.parent.in_decl_with_role(self.role_name()).lineNum)]))
        declaredVars = self.parent.declared_variables()
        errors = []
        for token in self.children[1].get_elements():
            if token.get_token() not in declaredVars:
                errors.append(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Undeclared variable:", pslErrors.color_token(token.get_token())]))
        if errors:
            raise pslErrors.SyntaxError('\n'.join(errors))

    def role_name(self):
        return self.children[0].role_name()

    def variables(self):
        """
        Returns the list of variables that may be used by the role associated with this in decl.
        """
        return [token.get_token() for token in self.children[1].get_elements()]


class OutDecl(PSLStmtNode):

    className = "Out Declaration"

    def class_name(self):
        return OutDecl.className

    @staticmethod    
    def parse(stmt, parent):
        node = OutDecl(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, outSyntax)
        return node

    def error_check(self):
        roleName = self.children[0].role_name()
        if roleName not in self.parent.role_names():
            raise pslErrors.SyntaxError([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Role name: ", pslErrors.color_token(roleName), 
                "not declared."])

    def role_name(self):
        return self.children[0].role_name()


class DefDecl(PSLStmtNode):
    """
    Encodes a def decl. Children:
    1. The role associated with these definitions.
    2. The list of definition pairs defined in this def statement.
    """

    className = "Def Declaration"

    def class_name(self):
        return self.className

    def role(self):
        return self.children[0].get_token()

    @staticmethod    
    def parse(stmt, parent):
        node = DefDecl(parent=parent)
        term = []
        colonEqualsFound = False
        pairComplete = False
        roleNameFound = False
        #Removing the period at the end, because we don't need (or want) it here.
        stmt.tokens, stmt.lineNums = stmt.tokens[:-1], stmt.lineNums[:-1]
        for token, lineNum in zip(stmt.tokens, stmt.lineNums):
            if token == 'Def' or token == '(' or token == ')':
                continue
            elif token == '=':
                break
            elif not roleNameFound:
                node.children.append(Token(node, [token], lineNum))
                roleNameFound = True
            elif roleNameFound:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Unexpected token: ", 
                    pslErrors.color_token(token) + ".", 
                "Expected a statement of the form:", pslErrors.color_token(' '.join(defSyntax.tokens))]))
        equalityIndex = stmt.tokens.index('=')
        defs = zip(stmt.tokens[equalityIndex+1:], stmt.lineNums[equalityIndex+1:])
        for token, lineNum in reversed(defs):
            if pairComplete and token == ',':
                pairComplete = False
                continue
            elif pairComplete:
                lastDef = node.children[-1]
                lastDefTokens = [lastDef.children[0], ':=']
                lastDefTokens.extend([token.get_token() for token in lastDef.children[1]])
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), 
                    "Missing comma before definition:", ' '.join(lastDefTokens)]))
            elif token == ',' and colonEqualsFound:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), 
                    "Missing identifier for term: ", ' '.join([token.get_token() for token in term]) + "."]))
            if colonEqualsFound:
                roleName = token
                node.children.append(DefPair(node, children=[roleName, list(reversed(term))], lineNum=lineNum))
                term = []
                colonEqualsFound = False
                pairComplete = True
            elif token == ':=':
                colonEqualsFound = True
            else:
                term.append(Token(node, [token], lineNum))
        if colonEqualsFound:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), 
                "Missing identifier for term: ", ' '.join([token.get_token() for token in term]) + "."]))
        return node

    def translate(self):
        return []

    def def_set(self):
        """
        Returns the maude term representing the set of definition pairs associated with this def decl.
        """
        return ', '.join([child.def_elem() for child in self.children[1:]])

    def def_pairs(self):
        """
        Returns the list of PSL Tree node objects that represent definition pairs.
        Note that the first child is the role associated with these definitions.
        """
        return self.children[1:]

        
class DefPair(Node):
    """
    A DefPair encodes a term of the form I := T, where I is an identifier (token), and T is a user-level term.
    The children are the string I, and a list of the tokens in T.
    """

    @staticmethod    
    def parse(stmt, parent):
        """
        Don't actually need to use this.
        """
        raise NotImplementedError()

    def role(self):
        return self.parent.role()
    
    def translate(self):
        """
        Not used, because defs show up outside the specification term.
        """
        return []

    def def_elem(self):
        return self.children[1] + ' := ' +  ' '.join([token.get_token() for token in self.children[2]])

    def shorthand(self):
        """
        Returns the identifier used as shorthand by the def as a string.
        """
        return self.children[0]

    def term(self):
        """
        Returns the (translated) term represented by the shorthand as a string.
        """
        term = []
        for token in self.children[1]:
            term.extend(token.translate())
        return ' '.join(term)


class StepStmt(PSLStmtNode):

    className = "Step Statement"

    def class_name(self):
        return StepStmt.className

    @staticmethod    
    def parse(stmt, parent):
        node = StepStmt(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, stepSyntax)
        return node

    def get_step_number(self):
        return self.children[0].value()

    def error_check(self):
        errors = self.disjoint_vars()
        errors.extend(self.no_new_vars_in_sent_msgs())
        if errors:
            raise pslErrors.StepError('\n'.join(errors))

    def disjoint_vars(self):
        """
        Let A and B be the roles in this step, where
        A is the sender and B is the receiver. Let
        t_a be the term sent by A, and t_b be the
        term received by B.
        Then, this function checks to make sure
        vars(t_a) and vars(t_b) are disjoint from the 
        vars of 
        every other role in this and all previous steps,
        with the exception of variables declared as 
        input. 
        """
        roleMap = self.parent.variables_per_role()
        declaredVars = self.parent.declared_variables()
        roleTermPairs = [(self.children[FIRST_ROLE_INDEX], self.children[FIRST_TERM_INDEX]), (self.children[SECOND_ROLE_INDEX], self.children[SECOND_TERM_INDEX])]
        errors = []
        checkedRoles = []
        for role, term in roleTermPairs:
            checkedRoles.append(role.role_name())
            inVars = set(roleMap[role.role_name()])
            otherStmtVars = self.parent.statement_vars(self.get_step_number())
            otherStmtVars = {roleName:otherStmtVars[roleName] for roleName in otherStmtVars if roleName not in checkedRoles}
            for var in [token.get_token() for token in term.get_tokens() if token.get_token() in declaredVars]:
                for roleName in otherStmtVars:
                    if var in otherStmtVars[roleName] and var not in inVars:
                        errorMsg = ' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Variable", pslErrors.color_token(var.strip()), 
                            "appears in the protocol terms of roles",
                            pslErrors.color_token(roleName), "and", pslErrors.color_token(role.role_name()) + ".",
                            "Variables must be disjoint between roles, with the possible exception of In(put) variables."])
                        if errorMsg not in errors:
                            errors.append(errorMsg)
        return errors

    def no_new_vars_in_sent_msgs(self):
        """
        Checks to make sure the sent message t in
        this step does not introduce any new variables.
        All variables in t were either declared in this
        role's input, or showed up in a previous
        message received by the sender.
        """
        senderRoleName = self.children[FIRST_ROLE_INDEX].role_name()
        inVars = set(self.parent.variables_per_role()[senderRoleName])
        statementVars = self.parent.statement_vars(self.get_step_number()-1)
        if statementVars:
            senderVars = statementVars[senderRoleName]
        else:
            senderVars = []
        sentTerm = ' '.join([token.get_token() for token in self.children[FIRST_TERM_INDEX].tokens()])
        sentTermVars = self.statement_vars()[senderRoleName]
        errors = []
        freshVars = [var for (var, sort) in self.get_root().get_protocol().var_name_sort_mapping().iteritems() if sort == "Fresh"]
        for var in sentTermVars:
            if var not in inVars and var not in senderVars and var not in freshVars:
                errors.append(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum), "Variable", pslErrors.color_token(var), "appears in neither", 
                    pslErrors.color_token(''.join(['In(', senderRoleName, ')'])), "nor in the previous received terms of", pslErrors.color_token(senderRoleName) + "."]))
        return errors

    def statement_vars(self):
        """
        Returns a mapping from role names (as strings) to the variables (as strings) that appear in that role.
        """
        firstRole = self.children[FIRST_ROLE_INDEX].role_name()
        secondRole = self.children[SECOND_ROLE_INDEX].role_name()
        declaredVars = self.get_root().get_protocol().declared_variables()
        firstRoleTokens = [token.get_token() for token in self.children[FIRST_TERM_INDEX].tokens()]
        secondRoleTokens = [token.get_token() for token in self.children[SECOND_TERM_INDEX].tokens()]
        firstRoleVars = [token for token in firstRoleTokens if token in declaredVars]
        secondRoleVars = [token for token in secondRoleTokens if token in declaredVars]
        return {firstRole:firstRoleVars, secondRole:secondRoleVars}


class Intruder(PSLSection):

    className = "Intruder"

    def class_name(self):
        return Intruder.className

    @staticmethod
    def parse(stmts, parent):
        root = Intruder(parent=parent)
        #Possible beginnings of each statement:
        #1. TermList
        #2. =>
        keywordStarts = [syntax for syntax in intrSyntax + varSyntax if syntax.tokens[0] != '_']
        underscoreStart = [intrSyntax[0], intrSyntax[2]]
        for stmt in stmts:
            for stmtType in keywordStarts:
                if stmt.tokens[0] == stmtType.tokens[0]:
                    root.children.append(stmtType.stmtNode.parse(stmt, root))
                    break
            else:
                stmtType = underscoreStart[0]
                try:
                    root.children.append(stmtType.stmtNode.parse(stmt, root))
                except pslErrors.SyntaxError:
                    stmtType = underscoreStart[1]
                    root.children.append(stmtType.stmtNode.parse(stmt, root))
        return root

    def error_check(self):
        pass


class IntrStmt(PSLStmtNode):

    className = "Intruder Statement"

    def class_name(self):
        return IntrStmt.className

    @staticmethod    
    def parse(stmt, parent):
        node = IntrStmt(parent=parent)
        if '=>' == stmt.tokens[0]:
            syntax = intrSyntax[1]
        elif '=>' in stmt.tokens:
            syntax = intrSyntax[0]
        elif '<=>' in stmt.tokens:
            syntax = intrSyntax[2]
        else:
            raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Invalid intruder statement. Expected a statement of one of the following forms:",
                '\n'.join(pslErrors.color_token(' '.join(syntax.tokens)) for syntax in intrSyntax)]))
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        return node

    def error_check(self):
        pass


class Attacks(PSLSection):

    className = "Attacks"

    def class_name(self):
        return Attacks.className

    @staticmethod
    def parse(stmts, parent):
        attPatternStmts = []
        node = Attacks(parent=parent)
        previousAttackNum = None
        for stmt in stmts:
            try:
                attackNum = int(stmt.tokens[0])
            except ValueError:
                attPatternStmts.append(stmt)
            else:
                if attPatternStmts:
                    node.children.append(AttPattern.parse(attPatternStmts, node, previousAttackNum))
                previousAttackNum = attackNum
                attPatternStmts = []
        if attPatternStmts:
            node.children.append(AttPattern.parse(attPatternStmts, node, attackNum))
        return node

    def declared_variables(self):
        """
        The declared variables of the attack section consists solely of the declared variables in the protocol section.
        """
        return self.parent.get_protocol().declared_variables()

    def var_name_sort_mapping(self):
        return self.parent.get_protocol().var_name_sort_mapping()

    def error_check(self):
        """
        Checks to make sure none of the attack patterns have the same number.
        """
        seenNumbers = {}
        for child in self.children:
            try:
                alreadyDeclaredLineNum = seenNumbers[child.attackNum]
            except KeyError:
                seenNumbers[child.attackNum] = child.lineNum
            except AttributeError:
                pass
            else:
                raise pslErrors.TranslationError([' '.join([pslErrors.error, pslErrors.color_line_number(child.lineNum), "Attack pattern", pslErrors.color_token(str(child.lineNum)), 
                    "already declared on line", pslErrors.color_token(str(alreadyDeclaredLineNum)) + "."])])


class AttPattern(Node):

    className = "Attack Pattern"

    def __init__(self, parent=None, op=None, children=None, lineNum=None, attackNum=-1):
        super(AttPattern, self).__init__(parent, op, children, lineNum)
        self.attackNum = attackNum

    def class_name(self):
        return AttPattern.className

    @staticmethod    
    def parse(stmts, parent, attackNum):
        attNode = node = AttPattern(parent=parent, attackNum=attackNum)
        stmtTypes = {'Subst':substSyntax, 'Intruder':learnsSyntax, 'With':constSyntax, 'with':constSyntax}
        reductionFlag = False
        for stmt in stmts:
            startToken = stmt.tokens[0]
            try:
                node.children.append(stmtTypes[startToken].stmtNode.parse(stmt, node))
            except KeyError:
                if 'without:' == startToken.lower() and reductionFlag:
                    raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmt.lineNums[0]), "Without blocks may not appear after the state-space reduction command."]))
                elif 'without:' == startToken.lower():
                    node = WithoutStmt(parent=attNode) 
                    attNode.children.append(node)
                elif 'state-space-reduction:' == startToken.lower():
                    reductionFlag = True
                elif 'avoid:' == startToken.lower() and reductionFlag:
                    node = Avoid(parent=attNode)
                    attNode.children.append(node)
                elif 'avoid:' == startToken.lower():
                    raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(stmts.lineNums[0]), "Avoid blocks are only allowed inside of state-space-reduction blocks."]))
                elif 'executes' in stmt.tokens:
                    if 'protocol' in stmt.tokens:
                        node.children.append(exeSyntax[0].stmtNode.parse(stmt, node))
                    else:
                        node.children.append(exeSyntax[1].stmtNode.parse(stmt, node))
                else:
                    currentLine = stmt.lineNums[0]
                    if startToken.lower() == "var" or startToken.lower == "vars":
                        errorMessage = ' '.join(["Variables may not be declared in the", pslErrors.color_token("Attacks"), "section. The Attacks section relies on variables declared in",
                            "the",  pslErrors.color_token("Protocol"), "section."])
                    else:
                        errorMessage = ' '.join(["Statement",
                        "is not a valid Attack statement. Valid attack statements cannot begin with:", pslErrors.color_token(stmt.tokens[0])])
                    raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(currentLine), errorMessage]))
        return attNode

    def translate(self):
        code = [str(self.attackNum) + " .{"]
        for child in self.children:
            code.extend(child.translate())
        code.append('}')
        return code

    def error_check(self):
        pass


class SubstStmt(PSLStmtNode):

    className = "Substitution Statement"

    def class_name(self):
        return SubstStmt.className

    @staticmethod    
    def parse(stmt, parent):
        node = SubstStmt(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, substSyntax)
        return node

    def get_role(self):
        return self.children[0]

    def error_check(self):
        if not self.get_role().role_name() in self.get_root().get_protocol().role_names():
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(self.lineNum),
                "Undeclared Role:", pslErrors.color_token(self.get_role().role_name())]))


class SubstList(Node):

    className = "Substitution List"

    def class_name(self):
        return SubstList.className

    @staticmethod
    def parse(stmt, parent):
        node = SubstList(parent=parent)
        term = []
        parsingTerm = True
        parsedVariable = False
        termLineNum = 0
        parsingRole = False
        for token, lineNum in reversed(zip(stmt.tokens, stmt.lineNums)):
            if parsingTerm and token != "|->":
                term.append((token, lineNum))
            elif parsingTerm and token == '|->':
                substMappingNode = SubstMapping(parent=node)
                termNode = Term(parent=substMappingNode, lineNum=term[0][1])
                termNode.children = [Token(termNode, [token], lineNum) for token, lineNum in reversed(term)]
                substMappingNode.children.append(termNode)
                term = []
                parsingTerm = False
            elif not parsingTerm and token == '|->': 
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Repeated token:", pslErrors.color_token(token)]))
            elif not parsingTerm and not parsedVariable and token != '|->':
                parsedVariable = True
                declaredVars = node.get_root().get_protocol().declared_variables()
                if token not in declaredVars:
                    raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Undeclared variable: ", pslErrors.color_token(token)]))
                else:
                    substMappingNode.children.append(Token(substMappingNode, [token], lineNum))
                node.children.append(substMappingNode)
            elif parsedVariable and token == ',':
                parsingToken = True
                parsedVariable = False
                parsingTerm = True
            elif parsedVariable and token != ',':
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Expected a comma before", 
                    pslErrors.color_token(substMappingNode.substitution_string())]))
        else:
            if not parsedVariable:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Incomplete substitution. First mapping missing variable."]))
            elif parsingTerm:
                raise pslErrors.SyntaxError(' '.join([pslErrors.error, pslErrors.color_line_number(lineNum), "Incomplete substitution. First mapping variable and mapping token:",
                pslErrors.color_token('|->') + "."]))
        return node

    def translate(self):
        return [', '.join([child.translate()[0] for child in self.children])]
    

            


    def error_check(self):
        super(SubstList, self).error_check()
        previousToken = ""
        declaredVars = self.get_root().get_protocol().statement_vars()
        inVars = self.get_root().get_protocol().variables_per_role()
        for role in declaredVars:
            declaredVars[role].extend(inVars[role])
        for child in self.children:
            if child.get_token() == "|->" and previousToken not in declaredVars[self.parent.get_role().role_name()]:
                raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(child.lineNum), "Variable ", pslErrors.color_token(previousToken), 
                    "does not appear in the protocol", "steps of role", pslErrors.color_token(self.parent.get_role().role_name()) + "."]))
            else:
                previousToken = child.get_token()
                    

class SubstMapping(Node):
    """
    Children:
    1. Term
    2. Variable
    So stored as Term <-| Variable
    """

    def substitution_string(self):
        return ' '.join([self.children[1].get_token(),'|->', ' '.join([token.get_token() for token in self.children[0].children])]) 

    def translate(self):
        return [' '.join([self.children[1].translate()[0], '|->', self.children[0].translate()[0]])]


class ExeStmt(PSLStmtNode):

    className = "Exe Statement"

    def class_name(self):
        return ExeStmt.className

    def get_role(self):
        return self.children[0]

    @staticmethod    
    def parse(stmt, parent):
        node = ExeStmt(parent=parent)
        if 'protocol' in stmt.tokens:
            syntax = exeSyntax[0]
        else:
            syntax = exeSyntax[1]
        node.op, node.children, node.lineNum = node._parse(stmt, syntax)
        return node

    def error_check(self):
        if self.children[0].role_name() not in self.get_root().get_protocol().role_names():
            raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(self.children[0].lineNum), "Undeclared Role", 
                pslErrors.color_token(self.children[0].role_name())]))


class LearnStmt(PSLStmtNode):

    className = "Learn Statement"

    def class_name(self):
        return LearnStmt.className

    @staticmethod    
    def parse(stmt, parent):
        node = LearnStmt(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, learnsSyntax)
        return node

    def error_check(self):
        pass


class ConstrStmt(PSLStmtNode):

    className = "Learn Statement"

    def class_name(self):
        return LearnStmt.className

    @staticmethod    
    def parse(stmt, parent):
        node = ConstrStmt(parent=parent)
        node.op, node.children, node.lineNum = node._parse(stmt, constSyntax)
        return node

    def error_check(self):
        pass


class WithoutStmt(PSLStmtNode):

    className = "Without Statement"

    def class_name(self):
        return WithoutStmt.className

    @staticmethod    
    def parse(stmt, parent):
        """
        Without's parse function should not be called explicitly.
        """
        raise NotImplementedError("A Without Block's parse function should not be called explicitly. The parsing of Without is built into the parsing of AttPattern")

    def translate(self):
        self.error_check()
        code = ["without:"]
        for child in self.children:
            code.extend(child.translate())
        return code

    def error_check(self):
        for child in self.children:
            if child.class_name() == IntrStmt.className:
                raise pslErrors.SyntaxError(' '.join[pslErrors.error, pslErrors.color_line_number(child.lineNum), "Intruder knowledge statements are not allowed inside of without blocks."])

class Avoid(WithoutStmt):
    """
    Avoid blocks are identical to without blocks, except that we allow intruder knowledge statements inside of avoid blocks.
    """

    className = "Avoid Statement"

    def class_name(self):
        return Avoid.className

    def error_check(self):
        pass


class DisequalityList(Node):
    """
    Encapsulates information about disequalities I != T where I is a variable name (token) and T is a user-defined term.
    """
    className = "Disequality List"
    def class_name(self):
        return DisequalityList.className

    @staticmethod    
    def parse(stmt, parent):
        node = DisequalityList(parent)
        tokens = ["$!=" if token == "!=" else token  for token in stmt.tokens]
        node.children = [Token(node, [token], lineNum) for token, lineNum in zip(tokens, stmt.lineNums)]
        node.lineNum = stmt.lineNums[0]
        return node

    def translate(self):
        self.error_check()
        return [child.translate() for child in self.children]

    def error_check(self):
        previousToken = None
        parent = self.parent
        for child in self.children:
            if child.get_token() == '$!=' and previousToken not in self.get_root().get_protocol().declared_variables():
                raise pslErrors.TranslationError(' '.join([pslErrors.error, pslErrors.color_line_number(child.lineNum), "Variable", pslErrors.color_token(child.get_token()), 
                    "must be declared in the", pslErrors.color_token("Protocol"), "section."]))
            previousToken = child.get_token()


class StatementSyntax(object):
    """
    Data structure that encapsulates information about a particular statement, consisting of:
    1. A tuple of tokens that define the statement.
    2. An iterable of Node subclasses defining the arguments to the statement.
    3. The type of Node this statement defines.
    """
    def __init__(self, tokens, stmtNode, argNodes):
        self.tokens = tokens
        self.argNodes = argNodes
        self.stmtNode = stmtNode

    def __repr__(self):
        return ''.join(['(', repr(self.tokens), ', ', repr(self.argNodes), ', ', repr(self.stmtNode), ')'])

specSyntax = [StatementSyntax(('spec_is'), Node, [Token])]

#Theory Syntax

class PSLList(object):
    """
    Encapsulates information about lists of arguments for PSL Syntax. This contains information on:
    1. The type of node that each element of the list should be.
    2. A regular expression representing the token(s) used as list delimiter
    3. Whether or not the list is allowed to be empty.
    """

    def __init__(self, elemType, delimiter='', canBeEmpty=False):
        """
        Observe that the default delimiter is empty. This is because by the time this class gets the list of tokens, all whitespace 
        removed. So a whitespace delimiter won't show up in the list of tokens. Instead, each separate token is an individual element
        of the list.
        Delimiters should be strings. 
        Delimiters should follow the Node interface.
        """
        self.elemType = elemType
        self.delimiter = delimiter
        self.canBeEmpty = canBeEmpty

    def parse(self, stmt, parent):
        """
        Note that unlike the Nodes, the parse method here is not static. This is because this object already exists (it encapsulates 
        information
        about lists for the syntax, remember), and we need information related to this instance: the delimiter and elemType.

        Furthermore, this version of parse takes a terminating token, that tells us when the list has reached its end. Note that in order 
        for this 
        function to work properly, it must be the case that the set of tokens in user-defined syntax is disjoint from the set of tokens in 
        the top level syntax.
        """
        elemTokens = []
        elemLineNums = [] 
        startingLineNum = None
        node = PSLListNode(parent, self.delimiter, [], startingLineNum)
        for token, lineNum in itertools.izip(stmt.tokens, stmt.lineNums):
            if startingLineNum is None:
                startingLineNum = lineNum
            if not self.delimiter:
                node.children.append(self.elemType.parse(Statement([token], [lineNum]), node))
            elif self.delimiter == token:
                node.children.append(self.elemType.parse(Statement(elemTokens, elemLineNums), node))
                elemTokens = []
                elemLineNums = []
            else:
                elemTokens.append(token)
                elemLineNums.append(lineNum)
        if elemTokens:
            node.children.append(self.elemType.parse(Statement(elemTokens, elemLineNums), node))
        assert all(node.children)
        return node

    def class_name(self):
        return ''.join(["List{", self.elemType.class_name(), ",", str(self.delimiter) if self.delimiter else ' ', "}"])



class OpTokens(object):
    className = "Op Token List" 

    def __init__(self):
        self.tokenList = PSLList(Token)

    def parse(self, stmt, parent):
        node = OpTokensNode()
        node.listNode = self.tokenList.parse(stmt, parent)
        return node

    def class_name(self):
        return self.className


class PSLListNode(Node):
    """
    A list of terms that have been parsed into a parse tree.
    Returned by the parse method of PSLList.
    """
    def __init__(self, parent, op, children, lineNum):
        """
        The op for a PSLList is the delimiter. The arguments are the elements of the list, and the lineNum is the line on which the list begins.
        """
        super(PSLListNode, self).__init__(parent, op, children, lineNum)

    def class_name(self):
        return "PSL List Node"

    def translate(self):
        op = ''.join([' ', self.op, ' '])
        childrenCode = []
        for child in self.children:
            childrenCode.extend(child.translate())
        return [op.join(childrenCode)]

    def get_elements(self):
        return self.children

    def append(self, elem):
        """
        Although this is not checked, elem should have the same interface as the rest of the elements in the list. Otherwise, bad things will happen.
        """
        #This assert isn't perfect (because it compares class rather than doing proper duck typing) but it was easy to write, and I found it helpful for debugging. Feel free to eliminate it, if you
        #want to take advantage of proper duck typing.
        assert self.children[0].__class__ == elem.__class__, "New elem: %s does not have the same class as the other elements in PSLListNode: %s" % (str(elem.__class__), str(self.children[0].__class__))
        self.children.append(elem)

    def extend(self, elemList):
        #This assert isn't perfect (because it compares class rather than doing proper duck typing) but it was easy to write, and I found it helpful for debugging. Feel free to eliminate it, if you
        #want to take advantage of proper duck typing.
        assert all(self.children[0].__class__ == elem.__class__ for elem in elemList)
        self.children.extend(elemList)


    def remove_range(self, startIndex, endIndex):
        """
        Given a starting index and an ending index, removes all elements e such that startIndex <= index(e) <= endIndex
        """
        self.args = self.args[:startIndex] + self.args[endIndex:]

    def remove(self, attributeString):
        """
        Given an attribute name as a string, removes the Token Node that contains that attributeString as its token.
        """
        for tokenNode in self.args:
            if tokenNode.get_token() == attributeString:
                self.args.remove(tokenNode)
                break

class OpTokensNode(Node):
    className = "Op Tokens Node"
    spaceRE = re.compile(r'\s')

    def __init__(self):
        self.listNode = None

    def class_name(self):
        return "Op Tokens Node"

    def translate(self):
        #A list of Tokens
        tokens = self.listNode.get_elements()
        translatedOp = ''
        previousTokenString = ''
        for token in tokens:
            tokenString = token.get_token()
            translatedOp = ' '.join([translatedOp, tokenString])

        assert False

    def get_elements(self):
        return self.listNode.get_elements()

    def append(self, elem):
        self.listNode.append(elem)

    def extend(self, elemList):
        self.listNode.extend(elemList)

    def remove_range(self, startIndex, endIndex):
        self.listNode.remove_range(startIndex, endIndex)

    def remove(self, attributeString):
        self.listNode.remove(attributeString)


def color_stmt_tokens(tokens):
    return map(pslErrors.color_top_level, tokens)


def color_user_tokens(userTokens, stmtTokens):
    return map(lambda token: pslErrors.color_top_level(token) if token in stmtTokens else pslErrors.color_token(token), userTokens)




typeSyntax = [
    StatementSyntax(['types', '_', '.'], TypeDecl, [PSLList(Token)]),
    StatementSyntax(['type', '_', '.'], TypeDecl, [PSLList(Token)]),
    StatementSyntax(['sort', '_', '.'], TypeDecl, [PSLList(Token)]),
    StatementSyntax(['sorts', '_', '.'], TypeDecl, [PSLList(Token)])
    ]
subTypeSyntax = [
    StatementSyntax(['subtype', '_', '.'], SubTypeDecl, [PSLList(PSLList(Token), delimiter='<')]),
    StatementSyntax(['subtypes', '_', '.'], SubTypeDecl, [PSLList(PSLList(Token), delimiter='<')]),
    StatementSyntax(['subsort', '_', '.'], SubTypeDecl, [PSLList(PSLList(Token), delimiter='<')]),
    StatementSyntax(['subsorts', '_', '.'], SubTypeDecl, [PSLList(PSLList(Token), delimiter='<')])
    ]
opSyntax = [
    StatementSyntax(['op', '_', ':', '_', '->', '_', '.'], OpDecl, [PSLList(Token), PSLList(Token), Token]),
    StatementSyntax(['op', '_', ':', '_', '->', '_', '[', '_', ']', '.'], OpDecl, [PSLList(Token), PSLList(Token), Token, 
        PSLList(Token)]),
    StatementSyntax(['op', '_', ':', '->', '_', '[', '_', ']', '.'], OpDecl, [PSLList(Token), Token, PSLList(Token)]),
    StatementSyntax(['op', '_', ':', '->', '_', '.'], OpDecl, [PSLList(Token), Token]),
    StatementSyntax(['ops', '_', ':', '->', '_', '.'], OpDecl, [PSLList(Token), Token]),
    StatementSyntax(['ops', '_', ':', '->', '_', '[', '_', ']', '.'], OpDecl, [PSLList(Token), Token, PSLList(Token)]),
    StatementSyntax(['ops', '_', ':', '_', '->', '_', '.'], OpDecl, [PSLList(Token), PSLList(Token), PSLList(Token), Token]),
    StatementSyntax(['ops', '_', ':', '_', '->', '_', '[', '_', ']', '.'], OpDecl, [PSLList(Token), PSLList(Token), Token, 
        PSLList(Token)])
    ]
varSyntax = [
    StatementSyntax(['var', '_', ':', '_', '.'], VarDecl, [PSLList(Token), Token]),
    StatementSyntax(['vars', '_', ':', '_', '.'], VarDecl, [PSLList(Token), Token])
    ]
eqSyntax = [
    StatementSyntax(['eq', '_', '=', '_', '.'], EqStmt, [Term, Term]),
    StatementSyntax(['eq', '_', '=', '_', '[', '_', ']', '.'], EqStmt, [Term, Term, PSLList(Token)])
    ]

#Specification Syntax
roleSyntax = StatementSyntax(['roles', '_', '.'], RoleDecl, [PSLList(Role)])

inSyntax = StatementSyntax(['In', '(', '_', ')', '=', '_', '.'], InDecl, [Role, PSLList(Token, ',')])
    
       
#Note: Def statements are parsed specially. See the DefDecl Node for details.
defSyntax = StatementSyntax(['Def', '(', '_', ')', '=', '_', '.'], DefDecl, [None, None])
        
outSyntax = StatementSyntax(['Out', '(', '_', ')', '=', '_', '.'], OutDecl, [Role, TermList])

FIRST_ROLE_INDEX = 1
SECOND_ROLE_INDEX = 2
FIRST_TERM_INDEX = 3
SECOND_TERM_INDEX = 4
stepSyntax = StatementSyntax(['_', '.', '_', '->', '_', ':', '_' ,'|-', '_', '.'], StepStmt, [Int, Role, Role, Term, Term])

#Intruder Syntax
intrSyntax = [
    StatementSyntax(['_', '=>', '_', '.'], IntrStmt, [TermList, TermList]),
    StatementSyntax(['=>', '_', '.'], IntrStmt, [TermList]),
    StatementSyntax(['_', '<=>', '_', '.'], IntrStmt, [TermList, TermList])]

#Attack Syntax
#&&&
#attSyntax = StatementSyntax(('_', '.', '_'), AttackBody, [Int, AttackBody])
substSyntax = StatementSyntax(['Subst', '(', '_', ')', '=', '_', '.'], SubstStmt, [Role, SubstList])
exeSyntax = [
    StatementSyntax(('_', 'executes', 'protocol', '.'), ExeStmt, [Role]),
    StatementSyntax(('_', 'executes', 'up', 'to', '_', '.'), ExeStmt, [Role, Int])
    ]
learnsSyntax = StatementSyntax(('Intruder', 'learns', '_', '.'), LearnStmt, [TermList])
constSyntax = StatementSyntax(('With', 'constraints', '_', '.'), ConstrStmt, [DisequalityList])
#We don't actually use this to parse without statements. Without statements are parsed while parsing an attack pattern
#withoutSyntax = StatementSyntax(('without:', '_'), WithoutStmt, [WithoutBody])

SECTION_HEADINGS = ["Theory", "Protocol", "Intruder", "Attacks", "Start"]

if __name__ == '__main__':
    tokenList = ["op", "s", ":", "Nat", "->", "Nat", '[', 'assoc', 'comm', ']', "."]
    print(OpDecl.parse(Statement(tokenList, [1] * len(tokenList))))


