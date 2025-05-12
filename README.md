## SeatSniperASU

I had a script that did this long ago, but it broke so I am writing a new one. In a nutshell, this aims to check for seat openings and ping a webhook based on activity (seats freeing or new course openings becoming available).

This does **NOT** enroll in the course for you - rather only notifies you based on activity based on configurable timing parameters.

****

### Dockerfile

There is a Dockerfile for convenience, it takes you into a shell in case you want to monitor multiple classes at once (see farther down, you will need to run multiple instances of the script). Builds and runs as you would expect:
```bash
sudo docker build -t seatsniper .
sudo docker run -it --rm seatsniper
```

From here, start one or more instances of the script based on your needs after adding a webhook.

#### Without Containerization

If you really do not want to use a Docker container you can install the requirements as follows from a virtual environment as well:
```bash
pip install -r requirements.txt
playwright install
playwright install-deps
```

****

### Webhooks

The json sent through the post request sent to the webhook is specifically hardcoded to work with Discord integrations, example:

- ![image](https://github.com/user-attachments/assets/bf82420b-e78f-4194-8f4a-d7040654c93b)

Provide the url via the `WEBHOOK_URL` environment variable once in the shell:
```bash
export WEBHOOK_URL="..."
```

****

### Watch Script

General usage:
```bash
usage: watch.py [-h] --subject SUBJECT --term TERM --number NUMBER [--sleep_time SLEEP_TIME]
watch.py: error: the following arguments are required: --subject, --term, --number
```
- Subject being the three letter catagory for any course, e.g. "CSE"
- Term following the "\<Season\> \<Year\>" format as on the actual site, if you do not provide this correctly the error will list all possible terms at the moment
- Number being the three digit course catalog number, e.g. "100"
- And sleep time being optional, but larger values are highly recommended to avoid being rate limits

Example usage:
```bash
./watch.py --subject CSE --number 571 --term "Fall 2025" --sleep_time 900 &
./watch.py --subject CSE --number 575 --term "Fall 2025" --sleep_time 900 &
```

What you will see (i.e., what is sent to the webhook):
1. Initial Discovery of courses (only happens once):
  - ![image](https://github.com/user-attachments/assets/79f2884a-734c-4e74-8100-4de9670af08d)
2. Seats being freed (happens either when a seat frees or more seats are added - yes this happens)
  - ![image](https://github.com/user-attachments/assets/607c0a8e-55c5-47f0-b947-d5a30b23623c)
