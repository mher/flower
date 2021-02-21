cmd="$@"

if [ ! -z "$FLOWER_SKIP_BROKER_READY" ]; then
	>&2 echo "Skipping broker readiness, executing command"
	exec $cmd
fi

while true;
do
	timeout 10 celery inspect ping
	STATUS=$?

	if [[ "$STATUS" == "143" ]]; then
		>&2 echo "Broker isn't responding"
		continue
	fi

	if [ -z "$FLOWER_SKIP_NODE_CHECK" ] && [[ "$STATUS" == "69" ]]; then
		>&2 echo "Nodes aren't responding"
		continue
	fi

	break

done

>&2 echo "Broker ready, executing command"
exec $cmd