import json

input_file = 'products_data.jsonl'
output_file = 'products_data_fixed.jsonl'

with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            p_id = item.get('id')
            
            # Construct new image URL
            new_image_url = f"https://ik.imagekit.io/RM/store/20160512512/assets/items/largeimages/{p_id}.jpg"
            
            # Update images list
            if 'images' in item and len(item['images']) > 0:
                item['images'][0]['uri'] = new_image_url
            else:
                item['images'] = [{'uri': new_image_url}]
            
            outfile.write(json.dumps(item) + '\n')
        except Exception as e:
            print(f"Error processing line: {e}")

print("Done.")
