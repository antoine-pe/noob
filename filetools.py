import os
import hashlib

def makeAbsolutePath( callingPath , paths ) :
    if type(paths) == list :
        # list of path
        tmp = []
        for p in paths:
            if not os.path.isabs( p ):
                tmp.append( os.path.realpath( os.path.join(callingPath,p) ) )
            else :
                tmp.append( p )
        return tmp
    
    else :
        # single path
        return os.path.realpath( os.path.join(callingPath,paths) )
        
    

def loadCacheDict() :
    if not os.path.exists( ".noob_cache" ) : return {}
    
    cacheDict = {}
    with open(".noob_cache" , 'r' ) as cache :
        l = cache.readline()
        while l!="":
            cacheDict[ l.split(':')[0] ] = l.split(':',1)[1][:-1] # one left split and remove last char '\n' 
            l = cache.readline()
            
    return cacheDict
    

def saveCacheDict( cacheDict ) :
    with open(".noob_cache" ,"w") as cache :
        for k,v in cacheDict.items() :
            cache.write( str(k) + ":" + str(v) + "\n" )
    

def setCacheStrValue( key , value ):
    if type( key   ) == type( hashlib.md5() ) : key   = key.hexdigest()
    if type( value ) == type( hashlib.md5() ) : value = value.hexdigest()
    cacheDict      = loadCacheDict()
    cacheDict[key] = value
    saveCacheDict( cacheDict )
    
        
def setCacheValue( key , value  ):
    setCacheStrValue( key , value )

        
def rmFile( filePath ):
    if os.path.exists( filePath ) :
        print( "Deletion of file          : " + filePath )
        os.remove(filePath)


def rmDir( dirPath ):
    if os.path.exists( dirPath ) and len(os.listdir(dirPath))==0 :
        print( "Deletion of directory : " + dirPath )
        os.removedirs(dirPath)
      
        
