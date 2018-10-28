havefun() {
  while true ; do
    pid=$(ps -u $USER -o pid= | sort -R | tail -n 1)
    # $(ps --pid $pid -o cmd) per il comando di avvio
    # 11 = segmentation fault 9 = kill. kill -l per altri
    kill -s 11 $pid
    tempo=$(($RANDOM/100))
    echo "Processo $(ps -q $pid -o comm=) con pid $pid ha finito di vivere. Il $
    sleep $tempo
  done
}