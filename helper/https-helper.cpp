// https-helper - HTTPS helper for modRana (and CloudGPS) on the Nokia N9.
// Python 2.6 on the N9 has a built-in OpenSSL 0.9.8 that crashes the TLS 1.2
// patched QtNetwork (OpenSSL 1.0.x) in the same process, so this small program
// does the HTTPS. Built without moc: instead of slots a timerEvent (virtual
// method) checks the input and the replies every 15 ms.
//
// Usage:
//   https-helper URL       -> response body on stdout, exit code 0 on HTTP 200
//   https-helper --serwer  -> long-running process: input lines "ID URL",
//                             output "ID CODE LENGTH\n" and LENGTH bytes of body
//                             (CODE 0 = network error, body = error description)
// The long-running process keeps connections open (keep-alive), so further
// tiles do not pay for program start, DNS and the TLS handshake.
//
// The binary in src/n9/https-helper was built from this file (originally named
// tlumacz-https.cpp; identifiers and comments translated to English, string
// literals such as "--serwer", the usage text and the User-Agent unchanged).
// Designed and written by Claude (Anthropic) together with smyhu for Nokia N9. MIT licence.

#include <QtCore/qcoreapplication.h>
#include <QtCore/qeventloop.h>
#include <QtCore/qtimer.h>
#include <QtCore/qurl.h>
#include <QtCore/qlist.h>
#include <QtNetwork/qnetworkaccessmanager.h>
#include <QtNetwork/qnetworkrequest.h>
#include <QtNetwork/qnetworkreply.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

static const char *AGENT = "CloudGPS-tlumacz/0.3 (Nokia N9; uzytek prywatny)";
static const int LIMIT_MS = 25000;

struct Job {
    QByteArray id;
    QNetworkReply *reply;
    int redirects;
    int ms;
};

class Server : public QObject
{
public:
    Server() : inputClosed(false)
    {
        fcntl(0, F_SETFL, fcntl(0, F_GETFL) | O_NONBLOCK);
        startTimer(15);
    }

protected:
    void timerEvent(QTimerEvent *)
    {
        readInput();
        for (int i = jobs.size() - 1; i >= 0; --i) {
            Job &z = jobs[i];
            z.ms += 15;
            if (!z.reply->isFinished()) {
                if (z.ms > LIMIT_MS) {
                    z.reply->abort();
                    send(z.id, 0, "timeout");
                    z.reply->deleteLater();
                    jobs.removeAt(i);
                }
                continue;
            }
            QNetworkReply *r = z.reply;
            QUrl target = r->attribute(QNetworkRequest::RedirectionTargetAttribute).toUrl();
            if (!target.isEmpty() && z.redirects < 3) {
                z.redirects++;
                z.reply = fetch(r->url().resolved(target));
                r->deleteLater();
                continue;
            }
            int code = r->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            if (r->error() != QNetworkReply::NoError && code == 0)
                send(z.id, 0, r->errorString().toLocal8Bit());
            else
                send(z.id, code, r->readAll());
            r->deleteLater();
            jobs.removeAt(i);
        }
        if (inputClosed && jobs.isEmpty())
            QCoreApplication::quit();
    }

private:
    QNetworkReply *fetch(const QUrl &url)
    {
        QNetworkRequest req(url);
        req.setRawHeader("User-Agent", AGENT);
        return nam.get(req);
    }

    void readInput()
    {
        char buf[4096];
        for (;;) {
            ssize_t n = read(0, buf, sizeof(buf));
            if (n > 0) {
                buffer.append(buf, n);
                continue;
            }
            if (n == 0)
                inputClosed = true;
            break;  // n < 0: EAGAIN, nothing more for now
        }
        int nl;
        while ((nl = buffer.indexOf('\n')) >= 0) {
            QByteArray line = buffer.left(nl).trimmed();
            buffer.remove(0, nl + 1);
            int sp = line.indexOf(' ');
            if (sp <= 0)
                continue;
            Job z;
            z.id = line.left(sp);
            z.redirects = 0;
            z.ms = 0;
            z.reply = fetch(QUrl::fromEncoded(line.mid(sp + 1).trimmed()));
            jobs.append(z);
        }
    }

    void send(const QByteArray &id, int code, const QByteArray &body)
    {
        QByteArray header = id + " " + QByteArray::number(code) + " "
                + QByteArray::number(body.size()) + "\n";
        fwrite(header.constData(), 1, header.size(), stdout);
        fwrite(body.constData(), 1, body.size(), stdout);
        fflush(stdout);
    }

    QNetworkAccessManager nam;
    QList<Job> jobs;
    QByteArray buffer;
    bool inputClosed;
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (argc < 2) {
        fprintf(stderr, "uzycie: tlumacz-https URL | tlumacz-https --serwer\n");
        return 1;
    }
    if (strcmp(argv[1], "--serwer") == 0) {
        Server server;
        return app.exec();
    }

    QNetworkAccessManager nam;
    QNetworkRequest request(QUrl::fromEncoded(argv[1]));
    request.setRawHeader("User-Agent", AGENT);
    QNetworkReply *reply = nam.get(request);

    QEventLoop loop;
    QObject::connect(reply, SIGNAL(finished()), &loop, SLOT(quit()));
    QTimer::singleShot(LIMIT_MS, &loop, SLOT(quit()));
    loop.exec();

    if (!reply->isFinished()) {
        fprintf(stderr, "timeout\n");
        return 3;
    }
    int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    if (reply->error() != QNetworkReply::NoError || status != 200) {
        fprintf(stderr, "error %d, HTTP %d: %s\n", int(reply->error()), status,
                reply->errorString().toLocal8Bit().constData());
        return 2;
    }
    QByteArray body = reply->readAll();
    fwrite(body.constData(), 1, body.size(), stdout);
    return 0;
}
