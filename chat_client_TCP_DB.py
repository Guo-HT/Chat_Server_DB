import threading
import socket
import re
import time


def send_to_server(client_socket, personal_id):
    while True:
        send_user = input('输入目标用户ID号码：')
        send_content = input('请输入要发送的数据：')
        send_pocket = personal_id + '\r\n' + send_user + '\r\n' + send_content
        client_socket.send(send_pocket.encode('gbk'))


def recv_pocket_match(recv_data):
    '''通过正则表达式，将接受的数据包中的目的ip及实际数据分开，并重新组包'''
    ret = re.match(r'^(.*)\r\n(.*)', recv_data)
    # 分组，第一组为发送用户ID， 第二组为数据内容
    return ret.group(1), ret.group(2)


def recv_from_server(client_socket):
    global exit_flag
    while True:
        # 接收服务器转发的消息
        recv_data_row = client_socket.recv(1024)
        try:
            # 正则匹配，提取信息
            recv_from, recv_content = recv_pocket_match(recv_data_row.decode('gbk'))
            # 输出消息
            print(f'\n》{recv_from}《给你发来消息：{recv_content}')
        except:
            print('未能连接到正确的服务器......请关闭程序后重试！')
            exit_flag = 1
            exit()


exit_flag = 0


def main():
    # 实例化socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 预设服务器IP地址及端口
    server_IP = input('请输入服务器IP地址:')
    server_addr = (server_IP, 8080)
    # 测试网络连接
    try:
        # 握手连接服务器
        client_socket.connect(server_addr)
    except:
        print('无法连接到服务器！\n请确认服务器地址正确及网络正常！')
        return

    personal_id=0
    choose = input('1->登录\n2->注册')
    if choose == '1':
        # 用户登录
        # 输入帐号、密码
        personal_id = input('请输入您的帐号ID：')
        personal_password = input('请输入密码：')
        personal_info = 'load' + '/' + personal_id + '/' + personal_password
        # 连接到服务器后直接发送用户帐号、密码
        client_socket.send(personal_info.encode('gbk'))
        # 接收服务器小心，判断其是否允许登录
        loading_allow = client_socket.recv(64).decode('gbk')
        if loading_allow == "no":
            print('登录失败！\n请重新运行！')
            return "登录失败"
        elif loading_allow == 'allow':
            print('\n登录成功!\n')
            pass
    elif choose == '2':
        reg_user_name = input('请输入您的用户名：')
        reg_user_password = input('请输入您的密码：')
        # 若条件满足，则用户正在注册新账户
        reg_info = 'reg' + '/' + reg_user_name + '/' + reg_user_password
        client_socket.send(reg_info.encode('gbk'))
        is_reg_success = client_socket.recv(64).decode('gbk')
        if is_reg_success != 'fail':
            reg_id = is_reg_success.count("\x00")  # 统计\x00
            print(f'->->->信息注册成功！\n用户帐号ID为{reg_id}\n重新开启后可登录！<-<-<-')
            return
        elif is_reg_success == 'fail':
            print('->->->信息注册失败！！！请重新开启后尝试！<-<-<-')
            return

    # 开启线程：从服务器接收消息
    t_recv = threading.Thread(target=recv_from_server, args=(client_socket,))
    t_recv.daemon = 1  # 设置线程守护为真
    t_recv.start()

    # 开启线程：向服务器发送消息
    t_send = threading.Thread(target=send_to_server, args=(client_socket, personal_id))
    t_send.daemon = 1  # 设置线程守护为真
    t_send.start()

    while True:
        if exit_flag == 1:
            print('关闭主线程！')
            exit()
        time.sleep(1)


if __name__ == "__main__":
    main()
