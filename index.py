# Based on https://realpython.com/blog/python/fingerprinting-images-for-near-duplicate-detection/

# USAGE
# python index.py --dataset images --shelve db.shelve

# import the necessary packages
import imagehash
import argparse
import shelve
import os
import os.path
import ffvideo

skip_first_seconds=5
steps_every_seconds=10
threshold = 10

valid_extentions = [ 'flv', 'mpeg', 'mp4', 'mkv', 'wmv' ]
def getLength(filename):
    length = -1
    try:
        video = ffvideo.VideoStream(filename)
        length = int(round(video.duration*1000))
    except:
        length = -1
    return length

def getVideoId(filename):
    size = os.path.getsize(filename)
    length = getLength(filename)
    id = str( size + length )
    return id, length

def createInitialIndex(db, dataset):
    for dirpath, dirnames, filenames in os.walk( dataset ):
        for filename in [f for f in filenames]:
            f = os.path.join( dirpath, filename )
            id, length = getVideoId( f )
            if length == -1:
                print "Invalid file: %s" % f
                continue

            if db.has_key( id ) == False:
                db[id] = { 'id': id, 'length': str(length), 'path': f, 'hashed': False, 'hashes': [] }
            else:
                print "File already indexed: %s" % filename

def indexVideo(filename):
    video = ffvideo.VideoStream(filename)
    hashes = []
    for t in xrange(skip_first_seconds, int(video.duration), steps_every_seconds):
        try:
            frame = video.get_frame_at_sec(t).image()
            hash = str(imagehash.dhash(frame))
            hashes.append( { 't': t, 'hash': hash } )
        except:
            print "Error processing file."

    return hashes


def indexVideos(db):
    for x in db:
        video = db[x]
        print "Indexing: %s" % video['path']
        if video['hashed'] == False:
            video['hashes']= indexVideo(video['path'])
            video['hashed'] = True
        else:
            print "hashes already calculated"

def searchHash(db, hashStr, skipArr):
    hash = imagehash.hex_to_hash(hashStr)
    skipSet = set(skipArr)
    results = []
    for x in db:
        video = db[x]
        if x in skipSet:
            continue

        if video['hashed'] == False:
            continue

        for h in video['hashes']:
            distance = imagehash.hex_to_hash(h['hash']) - hash
            if distance < threshold:
                results.append( { 'id': x, 't': h['t'], 'distance': distance })
    return results

def getFilename(db, id):
    return db[id]['path']

def searchDuplicates(db):
    alreadyScanned = []
    results = {}
    for x in db:
        results[x] = {}
        alreadyScanned.append(x)
        video = db[x]
        for h in video['hashes']:
            results[x][h['hash']] = []
            result = searchHash(db, h['hash'], alreadyScanned)
            if len( result ) > 0:
                results[x][h['hash']].append( result )

    # print "%s" % results
    for x in results:
        if len( results[x] ) > 0:
            print "Filename %s" % getFilename(db,x)
            for frame in results[x]:
                if len( results[x][frame] ) > 0:
                    for f in results[x][frame]:
                        for f2 in f:
                            print " -> distance: %d t: %d %s" % ( f2['distance'], f2['t'], getFilename(db, f2['id']) )

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dataset", required = True,
                help = "path to input dataset of videos")
ap.add_argument("-s", "--shelve", required = True,
                help = "output shelve database")
args = vars(ap.parse_args())

# open the shelve database
db = shelve.open(args["shelve"], writeback = True)
createInitialIndex(db, args["dataset"])
indexVideos(db)
# searchDuplicates(db)
#searchHash(db, "ff73a2c409133e00")
db.close()

