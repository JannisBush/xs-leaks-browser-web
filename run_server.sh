#!/usr/bin/env bash
source .env

start=$1
end=$2
step=$3
server=$4

cd automator
for (( i=$start; i<$end; i+=$step )) do
	now=$(date +"%T")
	echo "$now: Run from $i to $(( $i+$step ))"
	pipenv run python test_browsers.py local_grid $i $step $4
	TEST_PID=$!

done

trap ctrl_c INT

function ctrl_c() {
	cd ..
	kill $TEST_PID
	exit
}
