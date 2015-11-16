
from . exceptions import ParseError
from cvxLexer import cvxLexer
from ply import yacc
from . ast.expressions import Number, Parameter, Variable #, Sum, Transpose
from . properties.shape import Scalar, Shape, isscalar

#import ast
#http://www.google.com/url?q=http%3A%2F%2Fcvxr.com%2Fcvx%2Fdoc%2Ffuncref.html&sa=D&sntz=1&usg=AFQjCNEskkaqwhUSwDLxA59azIaw2jSIyQ


def _find_column(data, pos):
    last_cr = data.rfind('\n',0,pos)
    if last_cr < 0:
        last_cr = 0
    else:
        last_cr += 1 # since carriage return counts as a token
    column = (pos - last_cr) + 1
    return column

class cvxParser(object):
    # operator precedence
    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE'),
        ('right', 'UMINUS'),
        #('left', 'TRANSPOSE')
    )


    def __init__(self):
        self.lexerObj = cvxLexer()
        self.lexerObj.buildLex()
        self.tokens = self.lexerObj.tokens
        self.parserObj = yacc.yacc(module = self)  #define rules and uncomment this line to build parser.

        self.decl_parameters = {}
        self.decl_variables = {}
        self.decl_dimensions = set()
        self.decl_dual_variables = set()

        # while self.decl_parameters, self.decl_variables, and
        # self.decl_dimensions keep track of *declared* variables, parameters,
        # and dimensions, self.parameters, self.variables, and self.dimensions
        # keep track of *used* variables, parameters, and dimensions
        self.parameters = {}
        self.variables = {}
        self.dimensions = set()
        self.dual_variables = set()


    def _show_err(self, msg, lineno, lexpos):
        """ Prints a cvx4py parse error.
            lineno:
                the line number of the error
            lexpos:
                the lexer position
        """
        # get the entire string we just tried to parse
        data = self.lexerObj.lexer.lexdata
        s = data.split('\n')

        col = _find_column(data, lexpos)
        line = s[lineno-1]

        leader = 3*' '
        print "-"*72
        print "cvx4py error on line %s:" % lineno
        print leader, """>> %s """ % line.strip()
        print leader, "   " + (" "*(col-1)) + "^"
        print
        print "ERROR:", msg
        print "-"*72

    def parse(self, cvxProgramString):
        return self.parserObj.parse(cvxProgramString)  #uncomment once parser is implemented


    #implement a bunch of functions required for parser here
    #def p_program(self, p)  #https://github.com/cvxgrp/qcml/blob/master/src/qc_parser.py
        #pass


    def _name_exists(self,s):
        return (s in self.decl_dimensions) or \
               (s in self.decl_variables.keys()) or \
               (s in self.decl_parameters.keys())


    def _check_if_defined(self, identifier, lineno, lexpos):
        if self._name_exists(identifier):
            msg = "name '%s' already exists in namespace" % identifier
            self._show_err(msg, lineno, lexpos)
            raise ParseError(msg)

    def _check_dimension(self, identifier, lineno, lexpos):
        if not isinstance(identifier, int):
            if identifier in self.decl_dimensions:
                self.dimensions.add(identifier)
            else:
                msg = "name '%s' does not name a valid dimension" % identifier
                self._show_err(msg, lineno, lexpos)
                raise ParseError(msg)


    def p_program(self,p):
        '''program : statements objective statements
                   | statements objective
        '''
        constraints = p[1]
        if len(p) > 3: constraints.extend(p[3])
        constr = ProgramConstraints(constraints)
        data = ProgramData(self.variables)
        p[0] = codegen(p[2], constr, data)

    def p_program_empty(self,p):
        'program : empty'
        pass

    def p_empty(self,p):
        'empty : '
        pass


    def p_statements_statement(self,p):
        '''statements : statement NL
                      | statement SEMICOLON'''
        p[0] = p[1]

    def p_statements_many_statement(self,p):
        '''statements : statements SEMICOLON statement NL
                        | statements COMMA statement NL
        '''
        p[0] = []
        if p[1] is not None: p[0].extend(p[1])
        if p[2] is not None: p[0].extend(p[2])

    def p_statement(self,p):
        '''statement : create
                     | constraint
                     | dual_constraint
                     | empty
        '''
        #TO DO: add constraint, dual constraint and chained constrait to statement    | chained_constraint   | constraint  | dual_constraint

        if p[1] is not None: p[0] = p[1]
        else: p[0] = []

    def p_objective(self,p):
        '''objective : SENSE expression NL
                     | SENSE expression NL SUBJECT TO NL'''
        p[0] = ProgramObjective(p[1],p[2])



    def p_create_identifier(self,p):
        'create : VARIABLE array'
        (name, shape) = p[2]
        if(p[1] == 'variable'):
            self.decl_variables[name] = Variable(name, shape)

    def p_create_identifiers(self,p):
        'create : VARIABLES arraylist'
        if(p[1] == 'variables'):
            self.decl_variables.update({name: Variable(name, shape) for (name,shape) in p[2]})

    def p_create_dual_variable(self, p):
        'create : DUAL VARIABLE ID'
        self._check_if_defined(p[3], p.lineno(3), p.lexpos(3))
        self.decl_dual_variables.add(p[3])

    def p_create_dual_variables(self, p):
        'create : DUAL VARIABLES idlist'
        self.decl_dual_variables.update(p[3])

    def p_array_identifier(self,p):
        'array : ID LPAREN dimlist RPAREN'
        self._check_if_defined(p[1], p.lineno(1), p.lexpos(1))
        p[0] = (p[1], Shape(p[3]))

    def p_array_identifier_scalar(self, p):
        '''array : ID
                | ID LPAREN RPAREN
        '''
        self._check_if_defined(p[1], p.lineno(1), p.lexpos(1))
        p[0] = (p[1],Scalar())
     # for declaring multiple variables, parameters
    def p_arraylist_list(self,p):
        'arraylist : arraylist array'
        p[0] = p[1] + [p[2]]

    def p_arraylist_array(self,p):
        'arraylist : array'
        p[0] = [p[1]]

    # (for shape) id, id, id ...
    ##### dimlist modify

    def p_dimlist_list(self,p):
        '''dimlist : dimlist COMMA ID
                   | dimlist COMMA INT
        '''
        self._check_dimension(p[3], p.lineno(3), p.lexpos(3))
        p[0] = p[1] + [p[3]]

    def p_dimlist_singleton(self,p):
        '''dimlist : INT
                   | ID
        '''
        self._check_dimension(p[1], p.lineno(1), p.lexpos(1))
        p[0] = [p[1]]

    # (for declaring multiple dimensions) id id id ...
    def p_idlist_list(self,p):
        '''idlist : idlist ID'''
        self._check_if_defined(p[2], p.lineno(2), p.lexpos(2))
        p[0] = p[1] + [p[2]]

    def p_idlist_id(self,p):
        'idlist : ID'
        self._check_if_defined(p[1], p.lineno(1), p.lexpos(1))
        p[0] = [p[1]]



    def p_constraint(self,p):
        '''constraint : expression LOGICALEQUAL expression
                      | expression LESSTHANEQUAL expression
                      | expression GREATERTHANEQUAL expression
                      | expression LESSTHAN expression
                      | expression GREATERTHAN expression
        '''
        if p[2] == '==':
            p[0] = [p[1] == p[3]]
        elif p[2] == '<=':
            p[0] = [p[1] <= p[3]]
        elif p[2] == '>=':
            p[0] = [p[1] >= p[3]]
        elif p[2] == '<':
            p[0] = [p[1] < p[3]]
        else:
            p[0] = [p[1] > p[3]]

    def p_constraint_parens(self,p):
        ' constraint : LPAREN constraint RPAREN '
        p[0] = p[2]


    def p_dual_constraint(self,p):
        'dual_constraint : ID COLON constraint'
        if p[1] in self.decl_dual_variables:
            self.dual_variables.add(p[1])
            # a constraint is a singleton list
            p[3][0].dual_var = p[1]
        p[0] = p[3]


    #to do  Chain constraints



    def p_expression_add(self,p):
        'expression : expression PLUS expression'
        p[0] = p[1] + p[3] # expression + epxression

    def p_expression_minus(self,p):
        'expression : expression MINUS expression'
        p[0] = p[1] - p[3]


    def p_expression_divide(self,p):
        '''expression : expression DIVIDE INT
                        | expression DIVIDE FLOAT

        '''
        #|expression DIVIDE expression # to do #

        p[0] = Number(1.0/p[3]) * p[1]

    def p_expression_multiply(self,p):
        'expression : expression TIMES expression'
        p[0] = p[1] * p[3]

    def p_expression_group(self,p):
        'expression : LPAREN expression RPAREN'
        p[0] = p[2]

    def p_expression_negate(self,p):
        'expression : MINUS expression %prec UMINUS'
        p[0] = -p[2]


    def p_expression_transpose(self,p):
        'expression : expression TRANSPOSE'
        if isscalar(p[1]): p[0] = p[1]
        else: p[0] = Transpose(p[1])

    def p_expression_constant(self,p):
        '''expression : FLOAT
                      | INT
                      | ID'''
        # these are leaves in the expression tree
        if isinstance(p[1], float):
            p[0] = Number(p[1])
        elif isinstance(p[1], int):
            p[0] = Number(float(p[1]))

        else:
            variable = self.decl_variables.get(p[1], None)

            if not variable:
                msg = "Unknown identifier '%s'" % p[1]
                self._show_err(msg, p.lineno(1), p.lexpos(1))
                raise ParseError(msg)

            elif variable :
                p[0] = variable
                self.variables[p[1]] = variable


    def p_error(self, t):
        print("Syntax error at '%s'" % t.value)
