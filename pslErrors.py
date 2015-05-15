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
try:
    import termcolor  
except ImportError:
    print("termcolor module not installed. Error messages will not be in color.")
    term_color = False
else:
    try:
        termcolor.colored
    except AttributeError:
        print("termcolor claims to not have a colored method. Error messages will not be in color.")
        term_color = False
    else:
        term_color = True


class PSLError(Exception):
    """
    The root exception for all PSL errors. When raising exceptions, you should
    use one of the more specific errors below. This is for catching and 
    aggregating exceptions.
    """
    pass

class PSLWarning(Exception):
    """
    The root exception for all PSL warnings. When raising exceptions, you should
    use one of the more specific errors below. This is for catching and 
    aggregating exceptions.
    """
    pass

class LexingError(PSLError):
    """
    Raise this if we encounter an error during the lexing phase.
    """
    pass

class SyntaxError(PSLError):
    """
    Raise this if we encounter an error while parsing the specification (both
    at the Python level, and when interpreting Maude warnings).
    """
    pass

class ErrorsAndWarnings(Exception):
    """
    An aggregation of errors and warnings raised in lower levels of the 
    syntax tree. This should be thrown by any nodes whose error_check involves
    errors that may raise multiple kinds of errors (i.e. Warnings should print 
    a message and continue processing).
    """
    def __init__(self, message='', errors=None, warnings=None):
        super(ErrorsAndWarnings, self).__init__(message)
        self.errors = errors
        self.warnings = warnings

class MaudeError(PSLError):
    """
    Raise this if we encounter a maude error that we can't interpret.
    """
    pass

class FailedAssumptionError(PSLError):
    """
    Raise this if we have proved that the specification does not specify
    one of the assumptions required by the Maude-NPA (i.e. we found a 
    critical pair that could not be joined).
    """
    pass

class StepError(PSLError):
    """
    Raise this for any errors having to do with syntactically well-formed but incorrect Protocol Steps (i.e. variables are not disjoint).
    """
    pass

class TranslationError(PSLError):
    """
    Raise this if maude runs into a problem while performing the
    translation, and returns a term in the kind with at least one $$$ term.
    e.g. If we fail to construct an idempotent substitution.
    """
    pass

class FailedAssumptionWarning(PSLWarning):
    """
    Raise this if we failed to prove that the specification 
    satisfies one of the assumptions required by Maude-NPA, but we have 
    also failed to prove that it does NOT satisfy the assumption.
    e.g. the MTT times out, and without providing a proof one way or the
    other.
    """
    pass

class SyntaxWarning(PSLWarning):
    """
    Raise this if we encounter a warning in syntax that can be handled
    by Python (i.e. a sort that has been declared twice).
    """
    pass

class TranslationWarning(PSLWarning):
    """
    Raise this for warnings that don't fall under any of the other warning
    categories
    """
    pass

class InvalidOpError(PSLError):
    """
    Raise this error if an operator has an invalid combination of operator attributes:
    1. assoc without comm
    2. id without assoc and comm
    3. idem
    """
    pass

error = (termcolor.colored("ERROR Line:", 'red', attrs=['bold']) if
        term_color else "ERROR Line:")

errorNoLine = (termcolor.colored("ERROR", 'red', attrs=['bold']) if
        term_color else "ERROR")

warning = (termcolor.colored("WARNING Line:", 'yellow', 
    attrs=['bold']) if term_color else "WARNING Line:")
        

def color_line_number(line_num):
    """
    Shorthand for coloring the text of a line number green
    """
    if term_color:
        return termcolor.colored(str(line_num), 'green', attrs=['bold'])
    else:
        return str(line_num)


def color_text(text, color):
    """
    Short hand for coloring the specified text the specified color.
    """
    if term_color:
        return termcolor.colored(text, color, attrs=['bold'])
    else:
        return text

def color_top_level(text):
    """
    Colors top level syntax blue, to distinguish it from user-defined syntax. Colors underscores green, the same color as user-defined text.
    """
    return color_text(text, 'green') if text == '_' else color_text(text, 'blue')


def color_token(token):
    """
    Use to color tokens that are referenced in an error message, to make them
    stand out from the main text of the error message.
    """
    return color_text(token, 'green')


