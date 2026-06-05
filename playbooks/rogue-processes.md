# Fins rogue processes

Find the hog: lists every process sorted by CPU (-r), showing PID, CPU%, memory, and elapsed runtime. The 820% entry jumped out immediately.

```bash
ps -Ao pid,pcpu,pmem,etime,comm -r | head -20
```

 Identify what it was: full command line and parent PID for the hog. The flags (--headless --use-angle=swiftshader-webgl) revealed it was a headless Chromium GPU process doing software WebGL rendering.

 ```bash
 ps -o pid,ppid,lstart,command -p 81442
 ```

Trace the ancestry: walked up the parent chain (child → browser → daemon) until hitting the root, which turned out to be the orphaned agent-browser daemon parented to launchd.

```bash
ps -o pid,ppid,etime,command -p 96802 96845
```
