This program uses the Pyfhel library (python wrapper for the Microsoft SEAL FHE project) 
allow a server to perform a greyscaling algorithm on an image without learning information about the image.
The scripts implement the CKKS algorithm as this algorithm supports floating point operations on cipher texts,
which allows an easy way to perform the standard greyscaling average algorithm (R + G + B) / 3 on the encrypted channel values.

All encryption operations are provided by the Pyfhel libraries, and all image operations are provided by the 
PILLOW library. All code in the scripts was written by me.

The process is performed by converting the image to RGB channel values, dividing each channel into chunks of
size ~n/2, then encrypting each chunk into a cipher text with the Pyfhel library.
As the CKKS algorithm allows for n/2 slots per cipher text, storing n/2 numbers per cipher text will
maximize performance of the FHE operations performed.

To prevent memory errors on the socket side, the chunks are sent in batches to the server. The server performs 
the encrypted greyscaling average algorithm and returns a batch of single channel grey cipher text values.

When implementing this project breaking down the image into seperate information arrays which would 
allow for encryption, then reconstructing the image after decrypting the values was a challenge. 
The CKKS algorithm will pad unused cipher text slots with 0, which made it difficult to reshape the array into a size that
would be accepted by the PIL library for the original image dimensions. My relative unfamiliarity with python and numpy
was challenging as well as I was unsure as to the exact opertions done with numpy array operations such as stack and reshape.

The largest challenge was finding an acceptable method of sending large image files through the socket connection.
This needed to be done in batches to keep memory usage low enough, which comes at the cost of speed.
The largest file I have tested on the server is 8.3 megabytes(norway.jpg) and took around 6 minutes to complete on my pc.
Anything bigger than this and you run the risk of using more memory than is allowed for the python process by
the operating system.

Currently the project is very slow and is a memory hog. Memory optimizations could be made where large chunks of
image data are not required to be copied between different lists. And performance could be increased by 
parralelization through multi-threading of the encrytption operations.

As an aside I spent a good amount of time attempting to write my own implementation of the BGV algorithm in c++,
using this guide: https://bit-ml.github.io/blog/post/bgv-fully-homomorphic-encryption-scheme-in-python/.

If you are curious you can see the project here https://github.com/Andrew-Dron27/Privacy-Preserving-Image-Grayscaler.
I gave up when I couldnt get the FHE operations to produce the correct output values, and did not have the time 
to solve that along with implementing the key switching and modulus changing that would be needed for a true 
BGV implementations. This code is in the encryption folder

I spent more time trying to get the HELib library to work, however I am not sure how to best represent the integer
values as a cipher text with that library, and the given examples were very vauge as to how to encode multiple 
integer values in one cipher text.

The source files include the server.py script which runs a http server indefinitley, and the 
client.py script which will post encrypted data to the server for greyscaling.

I have included the sample_images folder that contains a few different file types and sizes that can be unused
with the scripts.


Instructions to run scripts:
The following libraries will need to be installed to run the scripts:

Numpy
pip install numpy

Pyfhel
pip install Pyfhel

I was having diffiuclties installing this library on windows with python3.12,
these commands form this page worked for me wtih this specific error:
https://stackoverflow.com/questions/77364550/attributeerror-module-pkgutil-has-no-attribute-impimporter-did-you-mean

python -m ensurepip --upgrade
python -m pip install --upgrade setuptools
python -m pip install Pyfhel


PILLOW
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade Pillow


In the source directory the server can be run on http:/localhost:8080 using the command:

python3 server.py

The server will run indefinitley until interrupted by the user.

The client script has the following argument structure:
python3 client.py server_url source_image_path dest_image_path

Here are some commands that can be run using the sample images provided. The scripts will run until complete then terminate.

Small jpeg:
python3 client.py http://localhost:8080 sample_images/nujabes.jpg sample_images/nujabes_grey.jpg

Large jpeg:
python3 client.py http://localhost:8080 sample_images/norway.jpg sample_images/norway_grey.jpg

Large bmp:
python3 client.py http://localhost:8080 sample_images/red_rock.bmp sample_images/red_rock_grey.bmp

Large png:
python3 client.py http://localhost:8080 sample_images/tahoma.png sample_images/tahoma_grey.png