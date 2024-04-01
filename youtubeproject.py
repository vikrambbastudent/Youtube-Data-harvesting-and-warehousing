from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st
from isodate import parse_duration
import matplotlib.pyplot as plt

#API key connection

def Api_connect():
    Api_Id="AIzaSyCql8tI-4l2D5ZHPgLV81T5b19eDhGyQhg"

    api_service_name="youtube"
    api_version="v3"

    youtube=build(api_service_name,api_version,developerKey=Api_Id)

    return youtube

youtube=Api_connect()


#get channels information
def my_channel_data(channel_id):
    request=youtube.channels().list(
                    part="snippet,ContentDetails,statistics",
                    id=channel_id
    )
    response=request.execute()

    for i in response['items']:
        data=dict(Channel_Name=i["snippet"]["title"],
                Channel_Id=i["id"],
                Subscribers=i['statistics']['subscriberCount'],
                Views=i["statistics"]["viewCount"],
                Total_Videos=i["statistics"]["videoCount"],
                Channel_Description=i["snippet"]["description"],
                Playlist_Id=i["contentDetails"]["relatedPlaylists"]["uploads"])
    return data

#get video ids
def my_videos_data(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id,
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=Playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids

#get video information
def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,ContentDetails,statistics",
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    Video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    Published_Date=item['snippet']['publishedAt'],
                    Duration=str(parse_duration(item['contentDetails']['duration'])),
                    Views=item['statistics'].get('viewCount'),
                    Likes=item['statistics'].get('likeCount'),
                    Comments=item['statistics'].get('commentCount'),
                    Favorite_Count=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_Status=item['contentDetails']['caption']
                    )
            video_data.append(data)    
    return video_data


#get comment information
def get_comment_info(video_ids):
    Comment_data=[]
    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                        Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        Comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'])

                Comment_data.append(data)

    except:
        pass
    return Comment_data

#get_playlist_details

#def get_playlist_details(channel_id):
       # next_page_token=None
       # All_data=[]
        #while True:
         #       request=youtube.playlists().list(
          #              part='snippet,contentDetails',
           #             channelId=channel_id,
            #            maxResults=50,
             #           pageToken=next_page_token
              #  )
               # response=request.execute()

                #for item in response['items']:
                 #       data=dict(Playlist_Id=item['id'],
                  #              Title=item['snippet']['title'],
                   #             Channel_Id=item['snippet']['channelId'],
                    #            Channel_Name=item['snippet']['channelTitle'],
                     #           PublishedAt=item['snippet']['publishedAt'],
                      #          Video_Count=item['contentDetails']['itemCount'])
                       # All_data.append(data)

                #next_page_token=response.get('nextPageToken')
                #if next_page_token is None:
                 #       break
        #return All_data


#upload to mongoDB
import certifi
ca = certifi.where()

client=pymongo.MongoClient("mongodb+srv://sifyvikram:1234@cluster0.56mochi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",tlsCAFile=ca)
db=client["Youtube_data"]

def channel_details(channel_id):
    ch_details=my_channel_data(channel_id)
    #pl_details=get_playlist_details(channel_id)
    vi_ids=my_videos_data(channel_id)
    vi_details=get_video_info(vi_ids)
    com_details=get_comment_info(vi_ids)

    coll1=db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,
                      "video_information":vi_details,"comment_information":com_details})

    return "upload completed successfully"


#Table creation for channels,playlists,videos,comments

def channels_table(c):

    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="1234",
                        database="Youtube_data")
    cursor = mydb.cursor()

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists channels(channel_id varchar(250) primary key,
                                                        channel_name varchar(250),
                                                        channel_description text,
                                                        channel_view bigint,
                                                        channel_subscribers bigint,
                                                        channel_video bigint,
                                                        Playlist_Id varchar(250))'''
    cursor.execute(create_query)
    mydb.commit()


    ch_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=pd.DataFrame(ch_list)
    #st.write(df)

    for index,row in df.iterrows():
        insert_query='''insert into channels (channel_id,
                                            channel_name,
                                            channel_description,
                                            channel_view,
                                            channel_subscribers,
                                            channel_video,
                                            Playlist_Id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Id'],
                row['Channel_Name'],
                row['Channel_Description'],
                row['Views'],
                row['Subscribers'],
                row['Total_Videos'],
                row['Playlist_Id'])
        
        #st.write(insert_query,values)  
        cursor.execute(insert_query,values)
        mydb.commit()

        



def videos_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="1234",
                        database="Youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                    Channel_Id varchar(100),
                                                    Video_Id varchar(30) primary key,
                                                    Title varchar(150),
                                                    Tags text,
                                                    Thumbnails varchar(200),
                                                    Description text,
                                                    Published_Date timestamp,
                                                    Duration time,
                                                    Views bigint,
                                                    Likes bigint,
                                                    Comments int,
                                                    Favorite_Count int,
                                                    Definition varchar(10),
                                                    Caption_Status varchar(50)
                                                        )'''

    cursor.execute(create_query)
    mydb.commit()


    single_channel_details= []
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name":channel_name_s},{"_id":0}):
        single_channel_details.append(ch_data["video_information"])

    df_single_channel= pd.DataFrame(single_channel_details[0])



    for index,row in df_single_channel.iterrows():
            insert_query='''insert into videos(Channel_Name,
                                                    Channel_Id,
                                                    Video_Id,
                                                    Title,
                                                    Tags,
                                                    Thumbnails,
                                                    Description,
                                                    Published_Date,
                                                    Duration,
                                                    Views,
                                                    Likes,
                                                    Comments,
                                                    Favorite_Count,
                                                    Definition,
                                                    Caption_Status
                                                )
                                                
                                                values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''


            values=(row['Channel_Name'],
                    row['Channel_Id'],
                    row['Video_Id'],
                    row['Title'],
                    row['Tags'],
                    row['Thumbnail'],
                    row['Description'],
                    row['Published_Date'],
                    row['Duration'],
                    row['Views'],
                    row['Likes'],
                    row['Comments'],
                    row['Favorite_Count'],
                    row['Definition'],
                    row['Caption_Status']
                    )


           
                
            cursor.execute(insert_query,values)
            mydb.commit()

             


def comments_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="1234",
                        database="Youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists comments(Comment_Id varchar(100) primary key,
                                                        Video_Id varchar(50),
                                                        Comment_Text text,
                                                        Comment_Author varchar(150),
                                                        Comment_Published timestamp
                                                        )'''

    cursor.execute(create_query)
    mydb.commit()

    single_channel_details= []
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name":channel_name_s},{"_id":0}):
        single_channel_details.append(ch_data["comment_information"])

    df_single_channel= pd.DataFrame(single_channel_details[0])

    for index,row in df_single_channel.iterrows():
            insert_query='''insert into comments(Comment_Id,
                                                    Video_Id,
                                                    Comment_Text,
                                                    Comment_Author,
                                                    Comment_Published
                                                )
                                                
                                                values(%s,%s,%s,%s,%s)'''


            values=(row['Comment_Id'],
                    row['Video_Id'],
                    row['Comment_Text'],
                    row['Comment_Author'],
                    row['Comment_Published']
                    )


            try:
                
                cursor.execute(insert_query,values)
                mydb.commit()

            except Exception as e:
                print(e)

def tables(channel_name):

    channels_table(channel_name) 
    videos_table(channel_name)
    comments_table(channel_name)

    return "Tables Created Successfully"

def show_channels_table():
    ch_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)

    return df


def show_videos_table():
    vi_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=st.dataframe(vi_list)

    return df2

def show_comments_table():
    com_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=st.dataframe(com_list)

    return df3

#streamlit part

with st.sidebar:
    st.header(":red[YOUTUBE DATA HAVERSTING AND WAREHOUSING]",divider="rainbow")
    

channel_id=st.text_input("Enter the channel ID")

if st.button("collect and store data"):
    ch_ids=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"]["Channel_Id"])

    if channel_id in ch_ids:
        st.success("Channel Details of the given channel id already exists")

    else:
        insert=channel_details(channel_id)
        st.success(insert)
    st.balloons()
#New code

all_channels= []
coll1=db["channel_details"]
for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
    all_channels.append(ch_data["channel_information"]["Channel_Name"])

unique_channel= st.selectbox("Select the Channel",all_channels)

if st.button("Migrate to Sql"):
    Table=tables(unique_channel)
    st.success(Table)
    st.balloons()

show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()


elif show_table=="VIDEOS":
    show_videos_table()

elif show_table=="COMMENTS":
    show_comments_table()

#SQL Connection

mydb=psycopg2.connect(host="localhost",
                    user="postgres",
                    password="1234",
                    database="Youtube_data",
                    port="5432")
cursor=mydb.cursor()

question=st.selectbox("Select your question",("1. All the videos and the channel name",
                                              "2. channels with most number of videos",
                                              "3. 10 most viewed videos",
                                              "4. comments in each videos",
                                              "5. Videos with highest likes",
                                              "6. likes of all videos",
                                              "7. views of each channel",
                                              "8. videos published in the year of 2022",
                                              "9. average duration of all videos in each channel",
                                              "10. videos with highest number of comments"))

if question=="1. All the videos and the channel name":
    query1='''select title as videos,channel_name as channelname from videos'''
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    df=pd.DataFrame(t1,columns=["video title","channel name"])
    st.write(df)
    # Add a bar chart
    channel_counts = df['channel name'].value_counts()
    plt.figure(figsize=(10, 6))
    channel_counts.plot(kind='bar')
    plt.xlabel('Channel Name')
    plt.ylabel('Number of Videos')
    plt.title('Number of Videos per Channel')
    st.pyplot(plt)
    st.balloons()

elif question=="2. channels with most number of videos":
    query2='''select channel_name as channelname,channel_video as no_videos from channels 
                order by channel_video desc'''
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    df2=pd.DataFrame(t2,columns=["channel name","No of videos"])
    st.write(df2)
    # Add a bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(df2["channel name"], df2["No of videos"], color='skyblue')
    plt.xlabel('Channel Name')
    plt.ylabel('Number of Videos')
    plt.title('Channels with Most Number of Videos')
    plt.xticks(rotation=45, ha='right')
    st.pyplot(plt)
    st.balloons()

elif question=="3. 10 most viewed videos":
    query3='''select views as views,channel_name as channelname,title as videotitle from videos 
                where views is not null order by views desc limit 10'''
    cursor.execute(query3)
    mydb.commit()
    t3=cursor.fetchall()
    df3=pd.DataFrame(t3,columns=["views","channel name","videotitle"])
    st.write(df3)
    # Add a stem chart
    plt.figure(figsize=(10, 6))
    plt.stem(df3.index, df3['views'], linefmt='b-', markerfmt='bo', basefmt=' ')
    plt.xlabel('Video Index')
    plt.ylabel('Number of Views')
    plt.title('10 Most Viewed Videos')
    st.pyplot(plt)
    st.balloons()

elif question=="4. comments in each videos":
    query4='''select comments as no_comments,title as videotitle from videos where comments is not null'''
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    df4=pd.DataFrame(t4,columns=["no of comments","videotitle"])
    st.write(df4)
    st.balloons()

elif question=="5. Videos with highest likes":
    query5='''select title as videotitle,channel_name as channelname,likes as likecount
                from videos where likes is not null order by likes desc'''
    cursor.execute(query5)
    mydb.commit()
    t5=cursor.fetchall()
    df5=pd.DataFrame(t5,columns=["videotitle","channelname","likecount"])
    st.write(df5)
    

elif question=="6. likes of all videos":
    query6='''select likes as likecount,title as videotitle from videos'''
    cursor.execute(query6)
    mydb.commit()
    t6=cursor.fetchall()
    df6=pd.DataFrame(t6,columns=["likecount","videotitle"])
    st.write(df6)
    st.balloons()

elif question=="7. views of each channel":
    query7='''select channel_name as channelname ,channel_view as views from channels'''
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    df7=pd.DataFrame(t7,columns=["channel name","totalviews"])
    st.write(df7)
    st.balloons()

elif question=="8. videos published in the year of 2022":
    query8='''select title as video_title,published_date as videorelease,channel_name as channelname from videos
                where extract(year from published_date)=2022'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    df8=pd.DataFrame(t8,columns=["videotitle","published_date","channelname"])
    st.write(df8)
    st.balloons()

elif question=="9. average duration of all videos in each channel":
    query9='''select Channel_Name as channelname,avg(Duration) from videos group by channel_name'''
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    df9=pd.DataFrame(t9,columns=["channelname","averageduration"])

    T9=[]
    for index,row in df9.iterrows():
        channel_title=row["channelname"]
        average_duration=row["averageduration"]
        average_duration_str=str(average_duration)
        T9.append(dict(channeltitle=channel_title,avgduration=average_duration_str))
    df1=pd.DataFrame(T9)
    st.write(df1)
    st.balloons()

elif question=="10. videos with highest number of comments":
    query10='''select title as videotitle, channel_name as channelname,comments as comments from videos where comments is
                not null order by comments desc'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    df10=pd.DataFrame(t10,columns=["video title","channel name","comments"])
    st.write(df10)
    st.balloons()