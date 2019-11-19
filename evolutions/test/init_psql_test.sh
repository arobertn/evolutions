

createuser -U postgres -d -PEe evtestuser
createdb -U evtestuser -E UTF8 evtest

echo "localhost:5432:evtest:evtestuser:evtestpass" >> ~/.pgpass
