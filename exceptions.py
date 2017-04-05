class RuntimeException( Exception ) :
    def __init__( self , msg ) : 
        Exception.__init__( self ) 
        self.msg  = msg 
    def __str__(self)         : return str(self.msg)


class AssertException( Exception ) :
    def __init__( self , msg ) : 
        Exception.__init__( self ) 
        self.msg = msg
    def __str__(self)         : return str(self.msg)