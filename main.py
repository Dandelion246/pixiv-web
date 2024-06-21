from pixiv import Pixiv

if __name__ == '__main__':
    p = Pixiv()
    # 获取所有关注的用户的所有作品
    p.download_user_following([84325201, 77504595])

