
scp root@www.zhixuan.com:/etc/redis.conf /etc/

scp root@www.eqcj.com:/etc/nginx/nginx.conf /etc/nginx/
scp root@www.eqcj.com:/etc/nginx/conf.d/* /etc/nginx/conf.d/

scp -r root@www.eqcj.com:/etc/supervisord* /etc/
scp root@www.eqcj.com:/etc/init.d/supervisord /etc/init.d/