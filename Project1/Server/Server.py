# Server side
from socket import *
from tqdm import tqdm
import os
import struct
import hashlib
import time

block_size = 5000


def socket_receive_message():
    global block_size
    server_port = 12000  # Declare the port which is unique
    server_socket = socket(AF_INET, SOCK_DGRAM)  # Choose UDP protocol
    server_socket.bind(('', server_port))

    print('The server is ready to receive')  # Guide message

    while True:
        message, client_address = server_socket.recvfrom(20480)  # Receive request message from client
        modified_message = message.decode()

        # Check the request information
        if modified_message[:16] == 'Request for file':

            # Make a header which consists of file's size and round_times and checksum
            file_path = modified_message[29:]
            round_times, header_message = make_header_info(file_path)
            server_socket.sendto(header_message, client_address)

            # Set the base variable of GBN window
            base = 0            # The pointer of begining of the window
            next_seq_num = 0    # The pointer of the next packet it will send
            window_size = 4  # Set the max number of packet it can send at once
            done = False   # Set a flag of completeness

            label = 0
            while not done:
                f = open(file_path, 'rb')   # Open the file
                f.seek(block_size*next_seq_num, 0)  # Set the file's pointer to assigned position
                data = f.read(block_size)    # Read the file

                # Calculate the length of file
                file_length = f.tell() - label
                file_segment = file_encapsulate(data, file_length, next_seq_num)

                # Send all packets in window
                if next_seq_num < base + window_size and not done:
                    server_socket.sendto(file_segment, client_address)

                    # Set the next send packet's position
                    next_seq_num = next_seq_num + 1

                    # If the file has been totally read
                    if not data:
                        done = True  # Set the flag to done
                        f.close()    # Close the file

                    # Try to receive ack before timeout
                try:
                    # Wait for ack
                    ack, client_address = server_socket.recvfrom(20480)

                    # Set the time of timeout
                    server_socket.settimeout(5.0)

                    # Get the result of whether message has been successfully sent
                    receive_seq_num, result = check_corrupt_message(ack)

                    if result is True:
                        base = base + 1  # Slide the window
                        label = f.tell()    # Move the pointer

                        # Reset the timeout to make sure the server is always online
                        if next_seq_num == round_times:
                            server_socket.settimeout(None)

                    # If we don't receive ACK or NAK before timeout
                except Exception:
                    print('Time out!')


def make_header_info(file_path):
    global block_size
    # Get the size of client wanted file
    file_size = os.path.getsize(file_path)
    # Calculate how many times it will loop
    round_times = calculate_round_times(file_size)
    # Get the checksum of whole file
    file_md5 = get_md5_whole(file_path)
    # Calculate the packet's size after data encapsulated
    segment_size = block_size + 100

    info = [file_size, round_times, block_size, segment_size, file_md5]
    print(info)
    # Transform header message to binary code
    header_message = struct.pack('!QQQQ', info[0], info[1], info[2], info[3]) + info[4].encode()
    return round_times, header_message


# According to the file_size to calculate the round times
def calculate_round_times(file_size):
    global block_size
    round_times = int(file_size / block_size)
    # If the file can been exactly divided
    if file_size == round_times * block_size:
        return round_times

    # If the file can not  been exactly divided
    else:
        return round_times + 1


# Make an UDP fragment
def file_encapsulate(file_segment, length, next_seq_num):
    global block_size
    # Get the checksum of per packet's data
    md5 = hashlib.md5(file_segment).hexdigest()
    # Encapsulate the data
    file_fragment = struct.pack('!QQ', length, next_seq_num) + file_segment + md5.encode()
    return file_fragment


# check the checksum
def check_corrupt_message(ack):
    # Get sequence number
    seq_num = struct.unpack('!Q', ack[:8])
    # Get ACK or NAK
    result = ack[8:].decode()

    # If receive ACK
    if result == 'Yes':
        return seq_num, True

    # If receive NAK
    else:
        return seq_num, False


# Get the whole md5
def get_md5_whole(file_path):
    f = open(file_path, 'rb')
    content = f.read()
    f.close()
    return hashlib.md5(content).hexdigest()


def main():
    socket_receive_message()


if __name__ == '__main__':
    main()
