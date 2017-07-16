from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import SimpleHTTPServer
import sys, os, zipfile

PORT = int(sys.argv[1])
paths = sys.argv[2]

def send_head(self):
    """Common code for GET and HEAD commands.

    This sends the response code and MIME headers.

    Return value is either a file object (which has to be copied
    to the outputfile by the caller unless the command was HEAD,
    and must be closed by the caller under all circumstances), or
    None, in which case the caller has nothing further to do.

    """
#    path = self.translate_path(self.path)
#    print path
    path = paths
    f = None

    if self.path.endswith('?download'):

        tmp_file = "tmp.zip"
        self.path = self.path.replace("?download","")

        zip = zipfile.ZipFile(tmp_file, 'w')
        for root, dirs, files in os.walk(path):
            for file in files:
                if os.path.join(root, file) != os.path.join(root, tmp_file):
                    zip.write(os.path.join(root, file))
        zip.close()
        path = self.translate_path(tmp_file)

    elif os.path.isdir(path):

        if not self.path.endswith('/'):
            # redirect browser - doing basically what apache does
            self.send_response(301)
            self.send_header("Location", self.path + "/")
            self.end_headers()
            return None
        else:

            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
    ctype = self.guess_type(path)
    try:
        # Always read in binary mode. Opening files in text mode may cause
        # newline translations, making the actual size of the content
        # transmitted *less* than the content-length!
        f = open(path, 'rb')
    except IOError:
        self.send_error(404, "File not found")
        return None
    self.send_response(200)
    self.send_header("Content-type", ctype)
    fs = os.fstat(f.fileno())
    self.send_header("Content-Length", str(fs[6]))
    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    return f

def list_directory(self, path):

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    import cgi, urllib

    """Helper to produce a directory listing (absent index.html).

    Return value is either a file object, or None (indicating an
    error).  In either case, the headers are sent, making the
    interface the same as for send_head().

    """
    try:
        list = os.listdir(path)
    except os.error:
        self.send_error(404, "No permission to list directory")
        return None
    list.sort(key=lambda a: a.lower())
    f = StringIO()
    displaypath = cgi.escape(urllib.unquote(self.path))
    f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
    f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
    f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
    f.write("<a href='%s'>%s</a>\n" % (self.path+"?download",'Download Directory Tree as Zip'))
    f.write("<hr>\n<ul>\n")
    for name in list:
        fullname = os.path.join(path, name)
        displayname = linkname = name
        # Append / for directories or @ for symbolic links
        if os.path.isdir(fullname):
            displayname = name + "/"
            linkname = name + "/"
        if os.path.islink(fullname):
            displayname = name + "@"
            # Note: a link to a directory displays with @ and links with /
        f.write('<li><a href="%s">%s</a>\n'
                % (urllib.quote(linkname), cgi.escape(displayname)))
    f.write("</ul>\n<hr>\n</body>\n</html>\n")
    length = f.tell()
    f.seek(0)
    self.send_response(200)
    encoding = sys.getfilesystemencoding()
    self.send_header("Content-type", "text/html; charset=%s" % encoding)
    self.send_header("Content-Length", str(length))
    self.end_headers()
    return f

Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
Handler.send_head = send_head
Handler.list_directory = list_directory

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    server = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()
