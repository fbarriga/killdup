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

skip_first_seconds = 5
steps_every_seconds = 10
threshold = 2

valid_extensions = ['mp4', 'avi', 'wmv', 'flv', 'mpg', 'mpeg', 'mov', 'mkv']


def get_video_length(filename):
    try:
        video = ffvideo.VideoStream(filename)
        length = int(round(video.duration * 1000))
    except:
        length = -1
    return length


def get_video_id(filename):
    size = os.path.getsize(filename)
    length = get_video_length(filename)
    video_id = str(size + length)
    return video_id, length


def create_initial_index(db, dataset):
    for dir_path, dir_names, filenames in os.walk(dataset):
        for filename in [f for f in filenames]:
            if filename.split('.')[-1].lower() not in valid_extensions:
                continue

            f = os.path.join(dir_path, filename)
            video_id, length = get_video_id(f)
            if length == -1:
                print "Invalid file: %s" % f
                continue

            if video_id not in db:
                db[video_id] = {'id': video_id, 'length': str(length), 'path': f, 'hashed': False, 'hashes': []}
                db.sync()
            # else:
            #     print "File already indexed: %s" % filename


def index_video(filename):
    video = ffvideo.VideoStream(filename)
    hashes = []
    for t in xrange(skip_first_seconds, int(video.duration), steps_every_seconds):
        # try:
        frame = video.get_frame_at_sec(t).image()
        frame_hash = str(imagehash.dhash(frame))
        hashes.append({'t': t, 'hash': frame_hash})
        # except:
        #     print "Error processing file."

    return hashes


def index_videos(db):
    for x in db:
        video = db[x]
        print "Indexing: %s" % video['path']
        if video['hashed'] is False or len(video['hashes']) == 0:
            try:
                video['hashes'] = index_video(video['path'])
                video['hashed'] = True
            except:
                print "Error processing file %s" % video['path']
            finally:
                db.sync()
                # else:
                #     print "hashes already calculated"


def search_hash(db, hash_str, skip_array):
    image_hash = imagehash.hex_to_hash(hash_str)
    skip_set = set(skip_array)
    results = []
    for x in db:
        video = db[x]
        if x in skip_set:
            continue
        if video['hashed'] is False:
            continue
        for h in video['hashes']:
            distance = imagehash.hex_to_hash(h['hash']) - image_hash
            if distance < threshold:
                results.append({'id': x, 't': h['t'], 'distance': distance})

    return results


def get_filename(db, video_id):
    return db[video_id]['path']

def search_duplicates(db):
    already_scanned = []
    results = {}
    for x in db:
        results[x] = {}
        already_scanned.append(x)
        video = db[x]
        for h in video['hashes']:
            results[x][h['hash']] = []
            result = search_hash(db, h['hash'], already_scanned)
            if len(result) > 0:
                results[x][h['hash']].append(result)

    # print "%s" % results
    for x in results:
        if len(results[x]) == 0:
            continue
        print "Filename %s" % get_filename(db, x)
        for frame in results[x]:
            if len(results[x][frame]) == 0:
                continue
            for f in results[x][frame]:
                for f2 in f:
                    print " -> distance: %d t: %d %s" % (f2['distance'], f2['t'], get_filename(db, f2['id']))

if __name__ == "__main__":
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dataset", required=True,
                    help="path to input dataset of videos")
    ap.add_argument("-s", "--shelve", required=True,
                    help="output shelve database")
    args = vars(ap.parse_args())

    # open the shelve database
    dbInstance = shelve.open(args["shelve"], writeback=True)
    create_initial_index(dbInstance, args["dataset"])
    print "Initial index created"

    index_videos(dbInstance)
    print "Videos indexed"

    # search_duplicates(db)
    # search_hash(db, "ff73a2c409133e00")
    dbInstance.close()
