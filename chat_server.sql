use chat_server
go

CREATE TABLE [dbo].[msg_queue] (
  [src] bigint  NULL,  /*消息源用户ID*/
  [dest] bigint  NULL,  /*消息目标用户ID*/
  [msg] varchar(255) COLLATE Chinese_PRC_CI_AS  NULL,  /*消息*/
  [is_send] int  NULL  /*是否发送：0否，1是*/
)  
ON [PRIMARY]


ALTER TABLE [dbo].[msg_queue] SET (LOCK_ESCALATION = TABLE)

CREATE TABLE [dbo].[user_table] (
  [id] int  IDENTITY(1,1) NOT NULL,  /*数据库自增生成ID账号*/
  [user_name] char(10) COLLATE Chinese_PRC_CI_AS  NOT NULL,  /*用户名*/
  [password] varchar(20) COLLATE Chinese_PRC_CI_AS  NOT NULL,  /*密码 明文保存*/
  [is_online] varchar(200) COLLATE Chinese_PRC_CI_AS  NOT NULL  /*保存socket信息，非0则在线*/
)  
ON [PRIMARY]


ALTER TABLE [dbo].[user_table] SET (LOCK_ESCALATION = TABLE)

go