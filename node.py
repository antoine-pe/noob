#from multiprocessing import Pool
import sys

class Node( object ) :
    
    def __init__( self ) :
        
        # graph properies
        self.parentNodeList = []
        self.childNodeList  = []
        
        # node properties
        self.nodeSequenceList = []
        self.nodeType         = "Generic Node"
        
        # build informations
        self.status       = "Not Processed"
        self.builtMessage = "Not Processed"
        
        # callbacks
        self.start_cb = None
        self.end_cb   = None
        
        self.parms_allowed = {
            "start_cb" : "callback to invoke when the evaluation of the node starts" , 
            "end_cb"   : "callback to invoke when the evaluation of the node ends"  
        }
        
        
    def depends( self , otherNode ) :
        if self      in otherNode.parentNodeList : otherNode.parentNodeList.remove( self      )
        if otherNode in self.childNodeList       : self     .childNodeList .remove( otherNode )
        self.parentNodeList.append( otherNode )
        otherNode.childNodeList.append( self ) 
    
    def name( self ) :
        return "Generic Node"
    
    def help( self ) :
        pass
    
    def getDependentList( self ) :
        nodeSequenceList = [ ] 
        nodeToVisitList  = [ self ]
        level            = 1
        
        # generate the linear sequence of dependencies ( Pixo's style ) 
        while len( nodeToVisitList ) != 0 :
            for node in nodeToVisitList[:] :
                for parent in node.parentNodeList :
                    if parent in nodeSequenceList : 
                        nodeSequenceList.remove( parent )
                    
                    nodeSequenceList.append( parent ) 
                    
                    if parent not in nodeToVisitList : nodeToVisitList.append( parent ) 
                
                nodeToVisitList.remove( node ) 
                
            level += 1
            
        nodeSequenceList = list( reversed( nodeSequenceList ) )
        
        return nodeSequenceList
        
        
    def execute( self , **kwargs ) : 
        
        self.nodeSequenceList = self.getDependentList()
        
        # for each node, compute the dependent sequence list
        for node in self.nodeSequenceList :
            node.nodeSequenceList = node.getDependentList() 
        
        # start the execution node by node
        for n in self.nodeSequenceList + [ self ] : 
            print( "-------------------------" )
            print( "Building '" + n.nodeType + "' , Target : \"" + n.name() + "\""  )
            
            # invoke start callback if defined
            if n.start_cb != None : n.start_cb( n )
            
            # evaluate the node
            n.evaluate( **kwargs )
            
            # invoke end callback if defined
            if n.end_cb != None : n.end_cb( n )
            
            if "Error" in n.status : sys.exit(-1)
        
    
    def __repr__( self ) :
        return self.name() # +":" + str(self.level)
        
        

