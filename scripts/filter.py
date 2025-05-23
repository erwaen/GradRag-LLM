import ijson
import json

input_file = "filtered2.json"
output_file = "filtered3.json"

with open(input_file, 'rb') as f_in, open(output_file, 'w') as f_out:
    f_out.write("[\n")
    first = True
    for obj in ijson.items(f_in, 'item'):
        if not (obj.get("note") == ""):
            if not first:
                f_out.write(",\n")
            json.dump(obj, f_out)
            first = False
    f_out.write("\n]")
