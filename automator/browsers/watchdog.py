#!/usr/bin/env python3
import subprocess
import time
import re
import sys

docker_ls = """docker container ls --format '{{println .Status "|" .Image "|" .ID }}'"""
pattern = re.compile("Up (\d+) minutes")

def main():
    stop_count = 0
    containers_to_stop = ["docker", "kill"]
    container_info = subprocess.check_output(docker_ls, shell=True).decode('utf-8').split('\n\n')[:-1]
    for line in container_info:
        # print(line)
        try:
            uptime, image, container_id = line.split("|")
            if not any([allowed in image for allowed in ["selenium", "redis", "rabbit"]]):
                m = pattern.match(uptime)
                if m is not None:
                    running_time = int(m.group(1))
                    if running_time >= 20:
                        containers_to_stop.append(container_id.strip())
                        stop_count += 1
                        pid = subprocess.check_output("docker inspect -f '{{.State.Pid}}' " + container_id.strip(), shell=True).decode("utf-8")[:-1]
                        subprocess.Popen(["sudo", "kill", "-9", pid])
        except ValueError:
            pass
    if stop_count > 0:
        #subprocess.Popen(containers_to_stop).pid
        print(f"Stopped {stop_count} old containers, all running {len(container_info)}")
        sys.stdout.flush()

if __name__ == '__main__':
    while True:
        main()
        time.sleep(60)
