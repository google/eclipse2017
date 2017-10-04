#!/bin/bash

mkdir -p $OUTPUT $MAP_DIR $RESCALED_DIR $CLASSIFY_DIR $CREDITS_DIR $MOVIE_DIR $MOVIE_RENUMBER_DIR $FINAL_DIR $SELECTED_DIR $CIRCLES_DIR

# Prep- only needs to be done once
# ffmpeg -i data/Megamovie_Intro.mp4 $VIDEO_SETTINGS -y $FINAL_DIR/Megamovie_Intro.mkv

# Generate list of all files
find $IMAGE_DIR -type f |grep -v \.jpg > files.txt

# Extract reliable image dimensions from all photos
python extract_image_dimensions.py \
       --files files.txt

# Prep- only needs to be done once
# Convert the umbra shapefiles to pickle
time python umbra_prep.py \
    --umbra_output $OUTPUT/umbra_polys.pkl &&

# Extract all the photo metadata to pickle
time python extract_metadata_from_datastore.py \
	   --project_id $PROJECT_ID \
	   --image_bucket $IMAGE_BUCKET \
	   --output $OUTPUT/extracted_metadata.pkl \
	   --directory $IMAGE_DIR \
	   --photo_table $PHOTO_TABLE \
	   --files $OUTPUT/files.txt &&

# Assign all the photos to umbra bins
time python umbra_photo.py \
       --input $OUTPUT/extracted_metadata.pkl \
       --umbra_polys $OUTPUT/umbra_polys.pkl \
       --umbra_photos $OUTPUT/umbra_photos.pkl &&

# Minor data manipulation for later steps
time python umbra_classifier.py \
       --umbra_photos $OUTPUT/umbra_photos.pkl \
       --input $OUTPUT/extracted_metadata.pkl \
       --umbra_polys $OUTPUT/umbra_polys.pkl \
       --photo_selections $OUTPUT/photo_selections.pkl \
       --image_directory $IMAGE_DIR \
       --selected_directory $SELECTED_DIR \
       --directory $CLASSIFY_DIR &&

# Rescale all photos which are assigned to an umbra bin based on sun disk
time python rescale_all_umbra_photos.py \
       --metadata $OUTPUT/extracted_metadata.pkl \
       --directory $IMAGE_DIR \
       --circles_directory $CIRCLES_DIR \
       --rescaled_directory $RESCALED_DIR \
       --photo_selections $OUTPUT/photo_selections.pkl &&

# Pick photos for each movie frame
time python choose_movie_frames.py \
       --metadata $OUTPUT/extracted_metadata.pkl \
       --directory $IMAGE_DIR \
       --rescaled_directory $OUTPUT/rescaled \
       --photo_selections $OUTPUT/photo_selections.pkl \
       --movie_frame_choices $OUTPUT/movie_frame_choices.pkl \
       --movie_stats $OUTPUT/movie_stats.txt \
       --umbra_polys $OUTPUT/umbra_polys.pkl &&

# Generate the map images with photo and sun location.
time python generate_maps.py \
    --input $OUTPUT/extracted_metadata.pkl \
    --directory $MAP_DIR \
    --umbra_polys $OUTPUT/umbra_polys.pkl \
    --eclipse_path_data data/eclipse_path_data.txt \
    --movie_stats $OUTPUT/movie_stats.txt \
    --data_directory data &&

# Render movie from photos and map images.
time python render_movie.py \
       --metadata $OUTPUT/extracted_metadata.pkl \
       --directory $IMAGE_DIR \
       --output_directory $MOVIE_DIR \
       --rescaled_directory $OUTPUT/rescaled \
       --photo_selections $OUTPUT/photo_selections.pkl \
       --umbra_polys $OUTPUT/umbra_polys.pkl \
       --data_directory data \
       --movie_stats $OUTPUT/movie_stats.txt \
       --map_directory $MAP_DIR &&

# Renumber movie frames to be sequential in case there were gaps
time python renumber_movie.py \
       --output_directory $MOVIE_DIR \
       --renumber_directory $MOVIE_RENUMBER_DIR &&

# Render the movie
time ffmpeg -i $MOVIE_RENUMBER_DIR/%05d.png -filter:v "setpts=0.5*PTS" $VIDEO_SETTINGS -y $FINAL_DIR/megamovie.mkv &&

# Render the credit frames
time python render_credits.py \
       --project_id $PROJECT_ID \
       --photo_table $PHOTO_TABLE \
       --additional_credits data/additional_credits.txt \
       --rename_credits data/rename_credits.txt \
       --credits_directory $CREDITS_DIR &&

# Render the credits movie
time ffmpeg -framerate 1 -i "$CREDITS_DIR/%05d.png" $VIDEO_SETTINGS -y $FINAL_DIR/credits.mkv &&

true
