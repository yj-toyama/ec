import json

# 設定
input_file = 'products_data.jsonl'
output_file = 'products_data_utf8.jsonl'

def convert_jsonl_to_utf8(input_path, output_path):
    print(f"変換を開始します: {input_path} -> {output_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip():
                continue
            
            # json.loads() は \uXXXX 形式を自動的にUnicode文字列に変換します
            data = json.loads(line)
            
            # ensure_ascii=False を指定することで、日本語をそのまま(UTF-8)出力します
            json.dump(data, f_out, ensure_ascii=False)
            f_out.write('\n')

    print("変換が完了しました。")

if __name__ == "__main__":
    convert_jsonl_to_utf8(input_file, output_file)