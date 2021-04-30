#!/bin/bash


if  [[ $(cat /dev/shm/FAN) -gt 100 ]] 

then 
	echo $1>dev/shm/HEAT 
else  
	echo "OFF" >/dev/shm/HEAT
fi

