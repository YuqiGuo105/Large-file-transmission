# Client side
from socket import *
from tqdm import tqdm
import struct
import hashlib
import os
import time


def socket_message_request():
    server_name = '127.0.0.1'
    # Others should not use this IP. You need to use ipconfig(win)
    # or ifconfig(linux, macos) to get you IP address in the network

    server_port = 12000
    client_socket = socket(AF_INET, SOCK_DGRAM)

    # Ask for the path for file
    message = input('Please input the path: ')

    # Send the request message
    request_message = 'Request for file, file_path: '.encode() + message.encode()
    client_socket.sendto(request_message, (server_name, server_port))

    # Receive the header_message
    header_message, server_address = client_socket.recvfrom(20480)
    file_size, round_times, block_size, segment_size = struct.unpack('!QQQQ', header_message[:32])
    file_md5 = header_message[32:].decode()
    # Print the head message as guide message
    print('file_size: ', file_size)
    print('round_times: ', round_times)
    print('block_size: ', block_size)
    print('segment_size: ', segment_size)
    print('file_md5: ', file_md5)

    # Receive the segment and resend the ack to notify the server
    f = open(message, 'wb')

    # Start the loop to receive the file
    for i in tqdm(range(round_times)):

        # Continue this while loop until this packet is ensure both correct and successfully will download
        end_this_pkt = False
        while not end_this_pkt:

            # Receive UDP segment
            file_segment, server_address = client_socket.recvfrom(segment_size)

            # Parse the data which has been encapsulated
            file_segment_length, file_segment_seq_num, file_segment_data, file_segment_md5 = parse_file(file_segment)

            # Check checksum and resend ACK or NAK to notify server
            ack, result = check_checksum(file_segment_data, file_segment_md5, file_segment_seq_num)

            # If checksum shows that segment is correct
            if result is True:
                # Write the data
                f.write(file_segment_data)

                # Resend ACK
                client_socket.sendto(ack, (server_name, server_port))
                end_this_pkt = True

            # If the checksum shows that segment is corrupted
            else:
                # Resend NAK
                client_socket.sendto(ack, (server_name, server_port))

    f.close()  # Close the file to finish

    # If the whole file is correct
    md5 = get_md5_whole(message)
    if file_md5 == md5:
        client_socket.close()   # Disconnect the connection with server
    else:
        socket_message_request()

# Get the checksum
def check_checksum(file_data, received_md5, seq_num):
    md5 = hashlib.md5(file_data).hexdigest()

    # If checksum is correct, resend ACK to server
    if md5 == received_md5:
        ack = struct.pack('!Q', seq_num) + 'Yes'.encode()
        return ack, True

    # If checksum is corrupted, resend NAK to server
    else:
        nak = struct.pack('!Q', seq_num) + 'No'.encode()
        return nak, False


# Get the whole md5
def get_md5_whole(file_path):
    f = open(file_path, 'rb')
    content = f.read()
    f.close()
    return hashlib.md5(content).hexdigest()


# Parse the file to get needed variable
def parse_file(file_segment):
    # Get the length of the file
    file_length = struct.unpack('!Q', file_segment[:8])[0]
    # Get the sequence number
    file_seq_num = struct.unpack('!Q', file_segment[8:16])[0]
    # Get data
    file_data = file_segment[16:16 + file_length]
    # Get checksum
    file_checksum = file_segment[16 + file_length:].decode()
    return file_length, file_seq_num, file_data, file_checksum


def main():
    socket_message_request()


if __name__ == '__main__':
    main()
