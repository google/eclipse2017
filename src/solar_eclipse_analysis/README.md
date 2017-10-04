Create conf.sh:

PROJECT_ID= # name of GCP project
IMAGE_BUCKET=megamovie # name of image_bucket to select images from
OUTPUT= # where to write output data, filesystem needs ~1TB free space
IMAGE_DIR= # directory containing all the input images
PHOTO_TABLE=Photo # Name of the photo table
MAP_DIR=$OUTPUT/map # where map output will be written
RESCALED_DIR=$OUTPUT/rescaled # where rescaled images will be written
CIRCLES_DIR=$OUTPUT/circles # where detected circles will be written
CLASSIFY_DIR=$OUTPUT/classify # where cloud vision classifications will be written
CREDITS_DIR=$OUTPUT/credits # where the credits output will be written
MOVIE_DIR=$OUTPUT/movie # where the movie output files will be written
MOVIE_RENUMBER_DIR=$OUTPUT/movie_renumber # where the renumbered movie files will be written
PARTITION_DIR=$OUTPUT/partition # where thre partitioned movie files will be written
FINAL_DIR=$OUTPUT/final # final directory where output files will appear
SELECTED_DIR=$OUTPUT/selected # where the list of selected images will be written
VIDEO_SETTINGS="-c:v libx264 -preset slow -crf 8" # video settings for movie encoding

Run make_movie.sh.
