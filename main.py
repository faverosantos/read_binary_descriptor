import serial
import datetime
import matplotlib.pyplot as plt
import numpy as np
from threading import Event, Thread
from time import sleep
import threading


HEADER_SIZE = 1                 #{i}-data-trailer
CHANNEL_NUMBER_SIZE = 1 	    # {0 -> 5}
FLAG_TIMEOUT_SIZE = 1     	    # Is a timeout package? 1: yes, 0: no
PACKAGE_COUNTER_SIZE = 3 	    # {000 -> 999}
TIMESTAMP_SIZE = 9	            # 10h 22m 15s 999ms: {102215999}
BUFFER_SIZE = 200
TMP_SIZE = 5 	                # {nível} + {0000 -> 9999}
TRAILER_SIZE = 2 	            # header-data-{f\n}
MESSAGE_SIZE = HEADER_SIZE+CHANNEL_NUMBER_SIZE+FLAG_TIMEOUT_SIZE+PACKAGE_COUNTER_SIZE+TIMESTAMP_SIZE+(BUFFER_SIZE*TMP_SIZE)+TRAILER_SIZE

CH0 = 0


FW_MINOR = 00
FW_MAJOR = 00

F_EMULADA = 10000

my_serial = serial.Serial()

class time_handler_c:
    seconds_counter = 0

class binary_description_c:
    has_data = False
    data_package = bytes(MESSAGE_SIZE)
    frequencies = np.zeros(30000)
    binary = np.zeros(30000)
    frequencies_counter = 0
    channel_number = 0
    is_timeout = 0
    package_counter = 0
    timestamp = bytes(9)
    st_level = 0
    qtd_st_level = 0
    nd_level = 0
    qtd_nd_level = 0


CH0_data = binary_description_c()
my_timer_handler = time_handler_c()


def calculate_area(frequencies):
    x = np.linspace(0, len(frequencies)-1, len(frequencies))*(1/F_EMULADA)
    return np.trapz(frequencies, x)


def one_second_tick():
    threading.Timer(1.0, one_second_tick).start()
    my_timer_handler.seconds_counter = my_timer_handler.seconds_counter + 1

    timestamp_cfg_message = prepare_timestamp()
    send_serial_data(timestamp_cfg_message)
    print("PY: Timestamp atualizado! :PY")

    if my_timer_handler.seconds_counter == 30:
        frequency_cfg_message = prepare_sampling_frequency()
        send_serial_data(frequency_cfg_message)
        print("PY: Frequencia de amostragem atualizada! :PY")
    elif my_timer_handler.seconds_counter == 60:
        my_timer_handler.seconds_counter = 0
        frequency_cfg_message = prepare_sampling_frequency()
        send_serial_data(frequency_cfg_message)
        print("PY: Frequencia de amostragem atualizada! :PY")


def get_serial_data():
    return my_serial.read_until().strip().decode("ascii")


def decode_data(received_data):
    if received_data[0] == 'i' and received_data[MESSAGE_SIZE-2] == 'f': # o \n do protocolo foi tirado pelo .strip() em get_serial_data()
        package = received_data[1:MESSAGE_SIZE-2]

        if int(package[0]) == CH0:
            CH0_data.has_data = True
            CH0_data.channel_number = int(package[0])
            CH0_data.is_timeout = int(package[1])
            CH0_data.package_counter = int(package[2:5])
            CH0_data.timestamp = package[5:14]
            data = package[14:MESSAGE_SIZE-2]

            position = 0
            for counter in range(0, BUFFER_SIZE):
                CH0_data.binary[position:position+int(data[1+counter*TMP_SIZE:(counter+1)*TMP_SIZE])] = int(data[counter*TMP_SIZE])
                position = position+int(data[1+counter*TMP_SIZE:(counter+1)*TMP_SIZE])


def send_serial_data(serial_message):
    my_serial.write(serial_message)


def prepare_frequency(app_channel):
    if app_channel == CH0:
        first_edge = 0
        second_edge = 0
        frequency = 0
        verification_buffer = [-1, -1]

        for counter in range(0,len(CH0_data.binary)):
            value = CH0_data.binary[counter]
            verification_buffer[1] = value

            if verification_buffer == [0, 1]:
                if first_edge == 0:
                    first_edge = counter
                elif first_edge != 0:
                    second_edge = counter

                    qtd_samples = second_edge - first_edge

                    frequency = F_EMULADA / qtd_samples
                    CH0_data.frequencies[first_edge:second_edge] = frequency

                    first_edge = second_edge

            verification_buffer[0] = verification_buffer[1]


def prepare_timestamp():
    now = datetime.datetime.now()

    hora = now.hour
    minuto = now.minute
    segundo = now.second
    milis = now.microsecond % 1000

    if hora < 9:
        hora_str = '0' + str(hora)
    else:
        hora_str = str(hora)

    if minuto < 9:
        minuto_str = '0' + str(minuto)
    else:
        minuto_str = str(minuto)

    if segundo < 9:
        segundo_str = '0' + str(segundo)
    else:
        segundo_str = str(segundo)

    if milis < 9:
        milis_str = '0' + str(milis)
    else:
        milis_str = str(milis)

    timestamp_str = str('i') + hora_str + minuto_str + segundo_str + milis_str + str("f\n")

    timestamp_cfg_message = bytes(timestamp_str, 'utf-8')

    return timestamp_cfg_message


def prepare_sampling_frequency():
    if F_EMULADA == 1000:
        frequency_cfg_message = b'iF10009999f\n'
    elif F_EMULADA == 2000:
        frequency_cfg_message = b'iF05009999f\n'
    elif F_EMULADA == 2500:
        frequency_cfg_message = b'iF04009999f\n'
    elif F_EMULADA == 5000:
        frequency_cfg_message = b'iF02009999f\n'
    elif F_EMULADA == 10000:
        frequency_cfg_message = b'iF01009999f\n'
    elif F_EMULADA == 12500:
        frequency_cfg_message = b'iF00809999f\n'
    elif F_EMULADA == 20000:
        frequency_cfg_message = b'iF00509999f\n'
    elif F_EMULADA == 40000:
        frequency_cfg_message = b'iF00259999f\n'
    elif F_EMULADA == 50000:
        frequency_cfg_message = b'iF00209999f\n'
    else:
        frequency_cfg_message = b'iF01009999f\n'

    return frequency_cfg_message


def config_serial():
    my_serial.baudrate = 115200
    my_serial.port = "/dev/ttyUSB2"
    my_serial.open()
    my_serial.reset_input_buffer()


if __name__ == '__main__':
    print("PY: Aloha from Python! :PY")
    print("PY: SW version is: " + str(FW_MAJOR) + "." + str(FW_MINOR) + " :PY")

    config_serial()
    print("PY: Serial configured! :PY")

    #one_second_tick()
    print("PY: Timer is configured! :PY")


    while(True):
        read_data = get_serial_data()
        print(read_data)

        decode_data(read_data)

        if CH0_data.has_data == True:
            CH0_data.has_data = False
            plt.plot(CH0_data.binary)
            plt.show()
            prepare_frequency(CH0)

            if CH0_data.is_timeout == 1:
                CH0_data.is_timeout = 0
                CH0_data.frequencies_counter = 0
                area = calculate_area(CH0_data.frequencies)
                print("PY: Area is: " + str(area) + " :PY")

                plt.plot(CH0_data.frequencies)
                plt.show()
                CH0_data.frequencies = np.zeros(30000)

        if read_data == "-- LPTmr configurado! --":
            send_serial_data(prepare_sampling_frequency())
            sleep(0.05)
            print("PY: Frequencia de amostragem atualizada! :PY")
            send_serial_data(prepare_timestamp())
            sleep(0.05)
            print("PY: Timestamp atualizado! :PY")
