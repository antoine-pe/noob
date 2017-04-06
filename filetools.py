import os


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
        
    
    

def md5raw( fpath ):
    hash = hashlib.md5()
    byteRead = 0
    chunkSize = 1024 #4096
#   maxByte = chunkSize
    
    with open( fpath, "rb") as f:
        for chunk in iter(lambda: f.read(chunkSize), b"") :
            byteRead += chunkSize
            hash.update(chunk)

    return hash#.hexdigest()
    
    

def setCacheStrValue( key , value  ):
    key   = key.hexdigest()
    
    if not os.path.exists( ".noob_cache" ) : 
        with open(".noob_cache" ,"w") as cache:
            cache.write( key + ":" + value + "\n"  )

    else:
        # parse the file
        md5Dic = {}
        with open( ".noob_cache" , 'r' ) as cache:
            l = cache.readline()
            while l != "" :
                md5Dic[ l.split(':')[0] ] = l.split(':',1)[1][:-1] # un seul split a gauche + suppression du car \n
                l = cache.readline()
        
        # set this md5
        md5Dic[key] = value
    
        # rewrite this file
        with open(".noob_cache" ,"w") as cache :
            for k,v in md5Dic.items() :
                cache.write( k + ":" + v + "\n"  )
            
        
def getCachedValue( key ):
    
    key   = key.hexdigest()
    
    if not os.path.exists( ".noob_cache" ) : return ""
    
    # parse this file
    md5Dic = {}
    with open(".noob_cache" , 'r' ) as cache :
        l = cache.readline()
        while l!="":
            md5Dic[ l.split(':')[0] ] = l.split(':',1)[1][:-1] # one left split and remove last char '\n' 
            l = cache.readline()
    
    # check if this file has a md5
    if key in md5Dic.keys() : 
        return md5Dic[key]
    else : 
        return ""


def setCacheValue( key , value  ):
    value = value.hexdigest()
    if type(value) != str:
        raise AssertionError("Cache Type Error : not a string " , str(type(value)) )
    setCacheStrValue( key , value )


        
def rmFile( filePath ):
    if os.path.exists( filePath ) :
        print( "Deletion of file          : " + filePath )
        os.remove(filePath)


def rmDir( dirPath ):
    if os.path.exists( dirPath ) and len(os.listdir(dirPath))==0 :
        print( "Deletion of directory : " + dirPath )
        os.removedirs(dirPath)
      
        
