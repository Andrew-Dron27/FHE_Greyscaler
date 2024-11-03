import numpy as np
from Pyfhel import Pyfhel, PyCtxt
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

def encode_encrypted_array(cipher_array):
    encoded = []
    for cipher in cipher_array:
        encoded.append([cipher[0].to_bytes().decode('cp437'), cipher[1].to_bytes().decode('cp437'),
                         cipher[2].to_bytes().decode('cp437')])
    return encoded

def decode_encrypted_array(encoded_array, HE):
    decoded = []
    for encoded in encoded_array:
        decoded.append([PyCtxt(pyfhel=HE, bytestring=encoded[0].encode('cp437')), PyCtxt(pyfhel=HE, bytestring=encoded[1].encode('cp437')),
                         PyCtxt(pyfhel=HE, bytestring=encoded[2].encode('cp437'))])
    return decoded

def greyscale_enc(r_c, g_c, b_c, HE):
    #Cxxs encryptions scheme allows floating point cipher texts
    #allowing for a mock divison operation
    ptxt_w = HE.encode(0.33)
    return (r_c + g_c + b_c) * ptxt_w

class handle_request(BaseHTTPRequestHandler):
    #post method takes buffer of shape [[r_ctxt, g_ctxt, b_ctxt]...] and applys the 
    #greyscale average method to the cipher text    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data)
        HE_server = Pyfhel()
        HE_server.from_bytes_context(json_data['context'].encode('cp437'))
        HE_server.from_bytes_public_key(json_data['public_key'].encode('cp437'))
        HE_server.from_bytes_relin_key(json_data['relin_key'].encode('cp437'))
        HE_server.from_bytes_rotate_key(json_data['s_rotate_key'].encode('cp437'))

        print("Decoding image data...")
        buffer = decode_encrypted_array(json_data['image_data'], HE_server)

        chunks = []

        print("Greyscaling image data...")
        for i in range(len(buffer)):
            r_chunk = buffer[i][0]
            g_chunk = buffer[i][1]
            b_chunk = buffer[i][2]
            res = greyscale_enc(r_chunk, g_chunk, b_chunk, HE_server)
            #using the greyscale average method, the rgb channels all have the same value
            chunks.append(res.to_bytes().decode('cp437'))
        
        print("Greyscaling complete")
        
        data = {
            'img_data' : chunks
        }

        print("Sending image data to client...")
        data_json = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data_json)))
        self.end_headers()
        
        self.wfile.write(data_json)


if __name__ == '__main__':
    host = "localhost"
    port = 8080

    server = HTTPServer((host, port), handle_request)
    print(f"Server started at http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

    server.server_close()


