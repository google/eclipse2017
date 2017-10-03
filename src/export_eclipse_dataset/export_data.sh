#!/bin/bash

source conf.sh
# mkdir -p $IMAGE_DIR $OUTPUT $OUTPUT_IMAGE_DIR

# # Copy all the photos to the local filesystem (warning: target FS
# # needs ~700GB free space)
# gsutil -m rsync  gs://${PROJECT_ID}-photos $IMAGE_DIR

# # List all photos
# find $IMAGE_DIR -type f | grep -v ".jpg"  > $OUTPUT/files.txt
# # Extract EXIF data from all photos
# time xargs -a $OUTPUT/files.txt -n 1 -P 64 ./exiftool_cmd &&

# # Extract photo and user metadata from datastore
# # and store results in pickle files
# time python extract_metadata_from_datastore.py \
# 	   --project_id $PROJECT_ID \
# 	   --photo_metadata $OUTPUT/photo_metadata.pkl \
# 	   --user_metadata $OUTPUT/user_metadata.pkl &&

# # Generate random IDs for mapping from user ID
# time python generate_random_id.py \
#  	   --user_metadata $OUTPUT/user_metadata.pkl \
#  	   --user_random_uuid $OUTPUT/user_random_uuid.pkl &&


# # Filter photos to ensure we only export valid photos
# # See metadata.py for inclusion criteria
# time python filter_photos.py \
# 	   --project_id $PROJECT_ID \
# 	   --photo_metadata $OUTPUT/photo_metadata.pkl \
# 	   --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl &&

# # Determine whether photo is in totality
# time python umbra_photo.py \
#        --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl \
#        --umbra_polys $OUTPUT/umbra_polys.pkl \
#        --umbra_photos $OUTPUT/umbra_photos.pkl \
#        --totality_output $OUTPUT/totality.pkl &&

# # Determine the state each photo is in
# time python determine_state.py \
#      --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl \
#      --google_maps_api_key $MAPS_KEY \
#      --state_output $OUTPUT/states.pkl

# # Convert extracted EXIF data from filtered photos to pickle files
# time python convert_exiftool_to_pickle.py \
#      --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl \
#      --directory $IMAGE_DIR \
#      --output_directory $OUTPUT_IMAGE_DIR \
#      --exif_directory $EXIF_DIR \
#      --exif_output $OUTPUT/exiftool.pkl &&

# Convert photo metadata to JSON format for upload to BigQuery
time python generate_photo_json.py \
     --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl \
     --exif_output $OUTPUT/exiftool.pkl \
     --json_output $OUTPUT/photos.json \
     --vision_labels /home/dek/src/solar_eclipse_analysis/cloud_vision_labels.pkl \
     --detected_circles /home/dek/src/solar_eclipse_analysis/detected_circles.pkl \
     --states $OUTPUT/states.pkl \
     --totality $OUTPUT/totality_output.pkl \
     --make_model_mobile data/make_model_mobile.csv \
     --user_random_uuid $OUTPUT/user_random_uuid.pkl &&

# # Create commands to strip image PII
# time python strip_image_pii.py \
#      --filtered_photo_metadata $OUTPUT/filtered_photo_metadata.pkl \
#      --json_output $OUTPUT/photos.json \
#      --exif_output $OUTPUT/exiftool.pkl \
#      --rename_credits data/rename_credits.txt \
#      --image_dir $IMAGE_DIR \
#      --output_image_dir $OUTPUT_IMAGE_DIR \
#      --user_metadata $OUTPUT/user_metadata.pkl \
#      --user_random_uuid $OUTPUT/user_random_uuid.pkl > cmds

# # Run the PII-stripping commands
# time bash cmds > output

# # Copy PII-stripped images back to GCS
# gsutil -m rsync $OUTPUT_IMAGE_DIR gs://${PROJECT_ID}_photos_stripped
true
