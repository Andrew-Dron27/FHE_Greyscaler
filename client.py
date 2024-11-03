import numpy as np
from PIL import Image
import math, sys, requests
from Pyfhel import Pyfhel, PyCtxt

def greyscale_enc(r_c, g_c, b_c, HE):
    ptxt_w = HE.encode(0.33)
    return (r_c + g_c + b_c) * ptxt_w

#Greyscale algorithm implemented client side
#used for testing purposes
def greyscale_client_side():
    n = 2**13
    HE = Pyfhel(context_params={'scheme':'ckks', 'n':2**13, 'scale':2**30, 'qi_sizes':[30]*5})
    HE.keyGen()             
    HE.relinKeyGen()
    HE.rotateKeyGen()

    image = Image.open("sample_images/sample3.bmp")
    image = image.convert("RGB")  

    image_array = np.array(image)
    height = image.height
    width = image.width

    #Get individual rgb channels into numpy arrays
    r_channel = image_array[:,:,0].flatten()
    g_channel = image_array[:,:,1].flatten()
    b_channel = image_array[:,:,2].flatten()

    print("Num Pixels ", len(r_channel))

    num_chunks = math.ceil(len(r_channel) / (n/2))

    print(f"[Client] Initializing Pyfhel session and data...")

    r_chunks = np.array_split(r_channel, num_chunks)
    g_chunks = np.array_split(g_channel, num_chunks)
    b_chunks = np.array_split(b_channel, num_chunks)
    grey_chunks_enc = np.array([])
    grey_chunks = np.array([])

    chunk_sizes = []

    print(f"Encrypting Data from image...")
    for i in range(len(r_chunks)):
        chunk_sizes.append(len(r_chunks[i]))
        r_chunk = HE.encrypt(r_chunks[i])
        g_chunk = HE.encrypt(g_chunks[i])
        b_chunk = HE.encrypt(b_chunks[i])
        res = greyscale_enc(r_chunk, g_chunk, b_chunk, HE)
        grey_chunks_enc = np.append(grey_chunks_enc, res)
    print(f"Successfully encrypted image data")

    print(f"Decrypting Data from image")

    for i in range(len(grey_chunks_enc)):
        res = HE.decrypt(grey_chunks_enc[i])[:chunk_sizes[i]]
        grey_chunks = np.append(grey_chunks, res)

    r_channel_dec = np.array(grey_chunks).reshape((height, width))
    g_channel_dec = np.array(grey_chunks).reshape((height, width))
    b_channel_dec = np.array(grey_chunks).reshape((height, width))
    
    rgb_array = np.stack((r_channel_dec, g_channel_dec, b_channel_dec), axis=2)
    new_image = Image.fromarray(rgb_array.astype('uint8'), 'RGB')

def encode_encrypted_array(cipher_array):
    encoded = []
    for cipher in cipher_array:
        encoded.append([cipher[0].to_bytes().decode('cp437'), cipher[1].to_bytes().decode('cp437'),
                         cipher[2].to_bytes().decode('cp437')])
    return encoded



def decrypt_image(enc_data, height, width, chunk_sizes, HE):
    grey_img_data = []
    [grey_img_data.append(PyCtxt(pyfhel=HE, bytestring=ctxt.encode('cp437'))) for ctxt in enc_data]
    r_chunks = np.array([])
    for i in range(len(grey_img_data)):
        r_chunks = np.append(r_chunks, HE.decrypt(grey_img_data[i])[:chunk_sizes[i]])

    #Reshape the decrypted array into dimensions suitable for the original image size
    r_channel_dec = np.array(r_chunks).reshape((height, width))
    rgb_array = np.stack((r_channel_dec, r_channel_dec, r_channel_dec), axis=2)

    return Image.fromarray(rgb_array.astype('uint8'), 'RGB')

    
def encrypt_image(image, chunk_sizes, HE):
    image = image.convert("RGB") 
    image_array = np.array(image)

    r_channel = image_array[:,:,0].flatten()
    g_channel = image_array[:,:,1].flatten()
    b_channel = image_array[:,:,2].flatten()

    #ckks supports n/2 slots per cipher text
    #split the image channels into (channels / (n / 2)) chunks
    num_chunks = math.ceil(len(r_channel) / (n/2))

    r_chunks = np.array_split(r_channel, num_chunks)
    g_chunks = np.array_split(g_channel, num_chunks)
    b_chunks = np.array_split(b_channel, num_chunks)

    enc_chunks = []
    for i in range(len(r_chunks)):
        chunk_sizes.append(len(r_chunks[i]))
        enc_chunks.append([HE.encrypt(r_chunks[i]), HE.encrypt(g_chunks[i]), HE.encrypt(b_chunks[i])])

    return enc_chunks


def send_enc_image(url, enc_data, HE):
    ctxt = HE.to_bytes_context().decode('cp437')
    pk = HE.to_bytes_public_key().decode('cp437')
    relin_key = HE.to_bytes_relin_key().decode('cp437')
    ro_key = HE.to_bytes_rotate_key().decode('cp437')

    data = {
        'context' : ctxt,
        'public_key' : pk,
        'relin_key' : relin_key,
        's_rotate_key' : ro_key,
        'image_data' : encode_encrypted_array(enc_data),
    }

    return requests.post(url, json=data)

if __name__=="__main__":

    if len(sys.argv) < 4:
        print("Please supply a server IP, file read and write paths as arguments")
        exit()

    server_url = sys.argv[1]
    r_file_path = sys.argv[2]
    w_file_path = sys.argv[3]

    #Init HE context and keys
    n = 2**13
    HE = Pyfhel(context_params={'scheme':'ckks', 'n':2**13, 'scale':2**30, 'qi_sizes':[30]*5})
    HE.keyGen()            
    HE.relinKeyGen()
    HE.rotateKeyGen()

    print(f"Opening image from filepath: ", r_file_path)
    image = Image.open(r_file_path)
    h = image.height
    w = image.width
    
    print(f"Encrypting image of size: (", h, 'x', w, ')')

    #store the size of each chunk to maintain accurate image size when decrypting
    chunk_sizes = []
    enc_image = encrypt_image(image, chunk_sizes, HE)

    print(f"Encryption complete")

    print(f"Sending image to server: ", server_url)
    
    #Buffer size in bytes = n/2 * x. 
    #Anything bigger than 128 will result in memory exceptions for large image files
    BUF_SIZE = 128
    dec_chunks = []

    #Send encrypted image in batches to avoid an out of memory exception
    i = 0
    while i < len(enc_image):
        buffer = []
        while len(buffer) < BUF_SIZE and i < len(enc_image):
            buffer.append(enc_image[i])
            i+=1
        print("Sent ", i, "chunks out of", len(enc_image), 'total')
        resp = send_enc_image(server_url, buffer, HE)
        if resp.status_code == 200:
            print('Recieved data chunk of size', len(resp.json()['img_data']), 'from server: ', server_url)
            [dec_chunks.append(c) for c in resp.json()['img_data']]
        else:
            print(f"Failed to retrieve image chunk. Aborting. Status code: {resp.status_code}")
        
    print('Decrypting image...')
    dec_image = decrypt_image(dec_chunks, h, w, chunk_sizes, HE)
    print ('Decryption complete')
    print('Writing image to path: ', w_file_path)
    dec_image.save(w_file_path)
        