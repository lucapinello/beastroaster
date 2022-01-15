#!/bin/bash


if  [[ $(cat /dev/shm/FAN) -gt 69 ]] 

then 
	echo $1>dev/shm/HEAT 
        pigs p 12 $1
else  
	echo "OFF" >/dev/shm/HEAT
        pigs p 12 0
fi

