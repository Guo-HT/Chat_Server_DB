import threading
import socket
import time
import re
import pymssql


socket_list = []


def recv_pocket_match(recv_data):
    '''通过正则表达式，将接受的数据包中的目的ip及实际数据分开，并重新组包'''
    try:
        ret = re.match(r'^(.*)\r\n(.*)\r\n(.*)', recv_data)
        # 分组，第一组为发送用户ID， 第二组为目标用户ID，第三组为数据内容
        return ret.group(1), ret.group(2), ret.group(3)
    except:
        pass


def personal_info_match(personal_info):
    '''通过正则表达式，将接收的用户登录信息数据包拆分为 用户账号 及 密码 ，并重新组包'''
    try:
        ret = re.match(r'^(.*)[/](.*)[/](.*)', personal_info)
        return ret.group(1), ret.group(2), ret.group(3)
    except:
        pass


def recv_from_client(client_socket, client_addr, database_info):
    '''接收客户端发送的数据'''
    # 初始化变量 user_id，存储用户ID信息，并供该函数全局使用
    user_id = str()
    func = str()
    con_temp = pymssql.connect(database_info[0], database_info[1], database_info[2], database_info[3], charset='cp936')
    cur_temp = con_temp.cursor()
    while True:
        try:
            # 循环接收该线程对应客户端发送的消息
            recv_data_row = client_socket.recv(1024)
            # 如果接收数据为空，decode报错，则捕获异常，断开连接
            recv_data = recv_data_row.decode('gbk')
            # 如果消息不为空,则不会抛出异常
            try:
                # 判断是 -用户ID- 还是 -实际消息-
                # 如果是 -实际消息- ，则正则提取
                resourse_id, dest_id, content = recv_pocket_match(recv_data)
                # 将发送的信息以元组存入消息队列列表中
                print('接收到消息！')
                # Msg_Queue.append((resourse_id, dest_id, content))
                sql_join_msg_queue = "insert into msg_queue values(%s, %s, %s, 0);"
                try:
                    cur_temp.execute(sql_join_msg_queue,
                                     (resourse_id.encode('cp936'), dest_id.encode('cp936'), content.encode('cp936')))
                    con_temp.commit()
                    print('数据库-消息队列-写入成功！')
                except:
                    print('数据库-消息队列-写入错误！！！')
                    con_temp.rollback()
            except:
                # 若正则提取报错，则认为接收的信息为用户输入的ID、密码
                func, id, password = personal_info_match(recv_data)
                # 判断为用户注册
                if func == 'reg':
                    sql_reg = 'insert user_table(user_name, password, is_online) values (%s, %s, 0);'
                    try:
                        cur_temp.execute(sql_reg, (id.encode('cp936'), password.encode('cp936')))  # 此处的id为用户自定义的用户名……
                        con_temp.commit()
                        sql_select_id = "select id from user_table where user_name=%s and password=%s;"
                        cur_temp.execute(sql_select_id, (id.encode('cp936'), password.encode('cp936')))
                        reg_id = cur_temp.fetchall()
                        print(reg_id[0][0])
                        client_socket.send(bytes(reg_id[0][0]))
                    except:
                        con_temp.rollback()
                        client_socket.send('fail'.encode('gbk'))

                # 判断为用户登录
                elif func == 'load':
                    print(f'用户上传ID:{id}  密码为:{password}')
                    # sql_check_info = 'select password from user_table where id=%s;'
                    sql_check_info = f'select password from user_table where id={int(id)};'
                    # cur.execute(sql_check_info, (int(id),))
                    cur_temp.execute(sql_check_info)
                    real_password_row = cur_temp.fetchall()
                    real_password = real_password_row[0][0]
                    if password != real_password:
                        client_socket.send('no'.encode('gbk'))
                        print(f"帐号id为{id}的用户登陆失败")
                        break
                    else:
                        client_socket.send('allow'.encode('gbk'))
                    user_id = id
                    print(user_id, '已连接……')
                    sql_set_online = "update user_table set is_online=%s where id=%s;"
                    try:
                        cur_temp.execute(sql_set_online, (str(client_socket).encode('cp936'), user_id.encode('cp936')))
                        con_temp.commit()
                    except:
                        print('登录(上线)状态修改错误！！！')
                        con_temp.rollback()
                    # 将该ID和当前tcp连接状态存入在线用户列表中
                    socket_list.append(client_socket)
                    # online_user.append([user_id, client_socket, client_addr])
        except:
            # recv()解堵塞，但接收到的数据包为空：当前连接断开
            try:
                # online_user.remove([user_id, client_socket, client_addr])
                socket_list.remove(client_socket)
                sql_set_offline = "update user_table set is_online='0' where id=%s;"
                cur_temp.execute(sql_set_offline, (user_id.encode('cp936'),))
                con_temp.commit()
            except:
                if func == "reg" or user_id == "":
                    print("客户端已断开连接!")
                else:
                    print('登录(下线)状态修改错误！！！')
                con_temp.rollback()
            client_socket.close()
            break
    # cur_temp.close()
    # con_temp.close()


def send_2_client(database_info):
    '''将服务端接受的消息分发给客户端'''
    con_send = pymssql.connect(database_info[0], database_info[1], database_info[2], database_info[3], charset='cp936')
    cur_send = con_send.cursor()
    sql_is_send = "update msg_queue set is_send=1 where src=%s and dest=%s and msg=%s;"
    while True:
        sql_wait_to_send = "select ut.is_online, mq.src, mq.dest, mq.msg from user_table ut, msg_queue mq where ut.is_online<>'0' and mq.is_send=0 and ut.id=mq.dest;"
        cur_send.execute(sql_wait_to_send)
        msg_queue = cur_send.fetchall()
        # print(msg_queue)
        for client_socket_str, src, dest, msg in msg_queue:
            send_pocket = str(src) + '\r\n' + str(msg)
            for socket_client in socket_list:
                if str(socket_client) == client_socket_str:
                    socket_client.send(send_pocket.encode('gbk'))
                    print('已发送!', end='')
                    try:
                        cur_send.execute(sql_is_send, (src, dest, msg.encode('cp936')))
                        con_send.commit()
                        print('并更改消息队列')
                        break
                    except:
                        print('消息队列更改错误！！！！！！')
                        con_send.rollback()
                        break
        time.sleep(0.1)


def output_msg(database_info):
    ''' 每隔2秒输出一次在线用户和消息队列 '''
    online_count = 0
    not_send = 0
    con_show = pymssql.connect(database_info[0], database_info[1], database_info[2], database_info[3], charset='cp936')
    cur_show = con_show.cursor()

    while True:
        sql_count_online = "select count(*) from user_table where is_online<>'0';"
        sql_count_send = "select count(*) from msg_queue where is_send=0;"
        try:
            cur_show.execute(sql_count_online)
            online_count = cur_show.fetchall()[0][0]
            cur_show.execute(sql_count_send)
            not_send = cur_show.fetchall()[0][0]
        except:
            pass
        finally:
            print('在线用户：', online_count)
            print('消息队列：', not_send)
        time.sleep(2)


def main():
    time.sleep(0.2)  # 程序开启时，pymssql模块会有warning，影响输入，故加入此延时
    db_ip = input("请输入数据库IP地址：")
    db_user = input("请输入数据库用户名：")
    db_password = input("请输入数据库密码：")
    db_name = input("请输入数据库名称：")
    database_info = [db_ip, db_user, db_password, db_name]
    # database_info = ['127.0.0.1', 'sa', '123456', 'chat_server']
    try:
        pymssql.connect(database_info[0], database_info[1], database_info[2], database_info[3], charset='cp936')
        print("数据库连接成功！")
    except:
        print("数据库连接失败！")
        return -1
    # 实例化socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定IP、端口
    server_addr = ('', 8080)
    server_socket.bind(server_addr)
    # 开启监听
    server_socket.listen(128)

    # 输出在线用户和消息队列
    threading.Thread(target=output_msg, args=(database_info,)).start()
    # 开启线程：向客户端发送消息
    threading.Thread(target=send_2_client, args=(database_info,)).start()

    while True:
        # 分配服务socket
        client_socket, client_addr = server_socket.accept()
        print(f'连接到用户{client_addr}')
        # 开启线程：接收客户端消息
        threading.Thread(target=recv_from_client, args=(client_socket, client_addr, database_info)).start()


if __name__ == "__main__":
    main()
