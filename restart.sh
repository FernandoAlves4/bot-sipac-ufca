#!/bin/bash
sudo systemctl restart bot-sipac
sleep 5
sudo systemctl status bot-sipac | head -3

