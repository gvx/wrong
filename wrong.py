#!/usr/bin/env python
# written for Python 2.6
"""Wrong
The Wrong Content Processor

defaults:
	publishdir: publish/
	sourcedir: ./
	css file: clever.css
	html template: template.html
	html home page: home.html
	resolve: crash
	destination extention: .html
	long date format: %A %d %B %Y (Friday 18 December 2009)
"""

from __future__ import print_function

__version__ = '0.0.0'

from optparse import OptionParser
import sys, os, os.path, shutil, re, time

class Settings:
	def __getattr__(self, attr):
		return self.__dict__.get(attr, None)
	def __setattr__(self, attr, value):
		self.__dict__[attr] = value
settings = Settings()

def log(*text):
	if settings.dbg:
		print(*text, file=sys.stderr)

def crash():
	print("Aborting...", file=sys.stderr)

def dodebug(*args, **kwargs):
	settings.dbg = True

def copyfile(filename):
	from_name = os.path.join(settings.sourcedir, filename)
	to_name = os.path.join(settings.publishpath, filename)
	if os.stat(from_name).st_mtime > os.stat(to_name).st_mtime:
		log("Copying", from_name, "to", to_name)
		shutil.copy2(from_name, to_name)
	else:
		log("Skipping", from_name)

def genpre(match):
	return '\n\n<pre class="story">'+match.group(1).replace('\n', '<br />')+'</pre>\n\n'

regexes = (
			(re.compile('(?<!_)_([^_]+?)_', re.M), r'<em>\1</em>'),
			(re.compile('__'), '_'),
			(re.compile('^#(.*?)\n', re.M), r'</p><h1 class="chapter">\1</h1><p class="story first">'),
			(re.compile('\n\n@\n(.*?)\n@\n\n', re.S), genpre),#r'\n\n<pre class="story">\1</pre>\n\n'),
			(re.compile('\n\n'), r'</p><p class="story">'),
			)
firstre = re.compile(r'!if:first!(.*?)!else!(.*?)!end!')
lastre = re.compile(r'!if:last!(.*?)!else!(.*?)!end!')
eachre = re.compile(r'!for:each!(.*?)!end!')
def processwrong(num, base, filename, first=False, last=False):
	log("Processing Wrong file",filename)
	source_fn = os.path.join(settings.sourcedir, base, filename)
	f = open(source_fn)
	txt = f.read().split('\n')
	f.close()
	t = {}
	i = 0
	for line in txt:
		line = line.strip()
		i += 1
		if not line:
			break
		if ':' in line:
			Key, Value = line.split(': ')
			t[Key] = Value
	if t.get('Date', 'Creation') == 'Creation':
		cdate = time.localtime(os.stat(source_fn).st_ctime)
		t['Date'] = time.strftime('%Y/%m/%d', cdate)
		t['LongDate'] = time.strftime(settings.longdate, cdate)
	else:
		t['LongDate'] = time.strftime(settings.longdate, time.strptime(t['Date'], '%Y/%m/%d'))
	t['Index'] = num
	t['Index+1'] = num+1
	t['Index-1'] = num-1
	#transform txt
	txt = txt[i:]
	txt = '\n'.join(txt)
	txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
	txt = txt.replace('--', '&mdash;').replace('...', '&hellip;')
	for rex, subst in regexes:
		txt = rex.sub(subst, txt)
	txt = ('<p class="story first">'+txt+'</p>').replace('<p class="story"></p>', '').replace('<p class="story first"></p>', '')
	t['Text'] = txt
	f = open(os.path.join(settings.publishpath, base, str(num)+settings.destext), 'w')
	tmp = template
	tmp = firstre.sub(first and r'\1' or r'\2', tmp)
	tmp = lastre.sub(last and r'\1' or r'\2', tmp)
	f.write(tmp.format(**t))
	f.close()
	return {'Index': num, 'Title': t['Title']}

def toint(string):
	istr = '0'
	for s in string:
		if not '0' <= s <= '9':
			break
		istr += s
	return int(istr)

def processtree(basedir, files=None):
	#basedir is the relative basedir, so that all the files can be found in settings.sourcedir+basedir
	log("Processing tree",basedir)
	dir = os.path.join(settings.sourcedir, basedir)
	wrongs = []
	if files is None:
		files = os.listdir(dir)
		if settings.sensibleignore:
			files = [x for x in files if not (x.startswith('.') or x.endswith('~'))]
		for ignoreitem in settings.ignore:
			ipath, ifile = os.path.split(ignoreitem)
			if ipath == basedir:
				if ifile in files:
					files.remove(ifile)
	for item in files:
		fn = os.path.join(dir, item)
		if fn in settings.ignore:
			log("Ignore",item)
			continue
		if os.path.isdir(fn):
			targetdir = os.path.join(settings.publishpath,basedir,item)
			log("Creating directory",fn,"in",targetdir)
			if not os.path.exists(targetdir):
				os.mkdir(targetdir)
			processtree(os.path.join(basedir,item)) #process tree
		else: #check whether this is a Wrong file
			f = open(fn)
			l = f.readline().strip()
			f.close()
			if l == 'Wrong':
				wrongs.append(item)
			else:
				fn = os.path.join(basedir, item)
				copyfile(fn)
	wrongs = sorted([(toint(k), k) for k in wrongs])
	problems = {}
	lastn = -1
	lastname = ''
	for n, name in wrongs:
		if n == lastn:
			if n in problems:
				problems[n].append(name)
			else:
				problems[n] = [lastname, name]
		else:
			lastn = n
			lastname = name
	if problems:
		key = None
		if settings.resolve == 'crash':
			print("wrong: could not resolve which Wrong file to select", file=sys.stderr)
			print("in {0}:".format(basedir), file=sys.stderr)
			for k in sorted(problems.keys()):
				print(*problems[k], file=sys.stderr)
			crash()
			exit()
		elif settings.resolve == 'alphabetic':
			pass
		elif settings.resolve == 'youngest':
			key = lambda f: os.stat(os.path.join(dir, f)).st_ctime
		elif settings.resolve == 'modified':
			key = lambda f: os.stat(os.path.join(dir, f)).st_mtime
		for k in problems:
			v = problems[k]
			v.sort(key=key, reverse=True)
			for t in v[1:]:
				for i,item in wrongs:
					if item == t:
						del wrongs[i]
						break
	f = wrongs[0][0]
	l = wrongs[-1][0]
	
	wlist = []
	for n, name in wrongs:
		wlist.append(processwrong(n, basedir, name, first=n==f, last=n==l))
	return wlist

def main():
	global template
	parser = OptionParser(version="%prog "+__version__)
	parser.add_option("-d", "--dbg", action="callback", callback=dodebug,
						help="enable debug mode: lots of things will be printed")
	parser.add_option("-p", "--publishdir", default=None, metavar="DIR",
						help="place processed files here")
	parser.add_option("-s", "--sourcedir", default=None, metavar="DIR",
						help="place files to be processed here")
	parser.add_option("-c", "--css", default=None, metavar="FILE",
						help="pick a custom (Clever)CSS file")
	parser.add_option("-t", "--template", default=None, metavar="FILE",
						help="pick a custom HTML template")
	parser.add_option("-H", "--home", default=None, metavar="FILE",
						help="pick a custom home page (HTML)")
	parser.add_option("-e", "--ext", default=None, metavar="FILE-EXT",
						help="define what filename extension to use for compiled Wrong files (default: .html)")
	parser.add_option("-i", "--ignore", action="append", default=None, metavar="FILE",
						help="ignore a file or directory (supply multiple times to ignore more paths)")
	parser.add_option("-I", "--dontignore", action="store_false", default=True, dest="sensibleignore",
						help="don't ignore things you normally want to ignore (.hidden, backup~)")
	parser.add_option("--clevercss", action="store_true", default=None,
						help="use CleverCSS to process the css file (default)")
	parser.add_option("--noclevercss", action="store_false",
						help="don't use CleverCSS")
	parser.add_option('-l', "--longdate", default=None, metavar="FORMAT",
						help='the format used for long dates, see Python docs for details (default: "%A %d %B %Y")')
	parser.add_option("-y", "--youngest", action="store_const", const="youngest",
						dest="resolve", default=None,
						help="posts with conflicting numbers are resolved by taking the youngest")
	parser.add_option("-m", "--modified", action="store_const", const="modified",
						dest="resolve",
						help="resolve by selecting the file last modified")
	parser.add_option("-a", "--alphabetic", action="store_const", const="alphabetic",
						dest="resolve",
						help="resolve alphabetically: pick 4b above 4a")
	parser.add_option("-x", "--crash", action="store_const", const="crash",
						dest="resolve",
						help="resolve by crashing and specifying what went wrong (even without --dbg) (default)")

	(options, args) = parser.parse_args()
	settings.publishdir = "publish/"
	settings.sourcedir = "./"
	settings.cssfile = "clever.css"
	settings.templatefile = "template.html"
	settings.homepagefile = "home.html"
	settings.destext = ".html"
	settings.sensibleignore = True
	settings.clevercss = True
	settings.resolve = "crash"
	settings.longdate = "%A %d %B %Y"
	try:
		f = open(os.path.expanduser('~/.config/wrongrc'))
		log("Opened wrongrc")
		for line in f:
			if '#' in line:
				line = line[:line.index('#')]
			if '=' in line:
				key, val = line.split('=')
				setattr(settings, key.strip(), val.strip())
		f.close()
	except IOError:
		pass
	if options.publishdir:
		settings.publishdir = options.publishdir
	if options.sourcedir:
		settings.sourcedir = options.sourcedir
	if options.css:
		settings.cssfile = options.css
	if options.template:
		settings.templatefile = options.template
	if options.home:
		settings.homepagefile = options.home
	if not options.sensibleignore:
		settings.sensibleignore = options.sensibleignore
	if options.clevercss is not None:
		settings.clevercss = options.clevercss
	if options.resolve:
		settings.resolve = options.resolve
	if options.ext:
		settings.destext = options.ext
	if options.longdate:
		settings.longdate = options.longdate
	if options.ignore:
		settings.ignore = options.ignore
	elif not settings.ignore:
		settings.ignore = ["publish"]

	#settings.publishpath = os.path.join(settings.sourcedir, settings.publishdir) #ouch
	settings.publishpath = settings.publishdir

	if not os.path.exists(settings.publishpath):
		os.makedirs(settings.publishpath)

	if settings.clevercss:
		try:
			import clevercss
		except ImportError:
			log("Continuing without CleverCSS")

	basedir_files = os.listdir(settings.sourcedir)
	log('Files in base dir:')
	log('   '.join(basedir_files))
	if settings.cssfile not in basedir_files:
		print("CSS file not found!")
		return crash()
	if settings.clevercss:
		f_r = open(os.path.join(settings.sourcedir, settings.cssfile))
		f_w = open(os.path.join(settings.publishpath, settings.cssfile), 'w')
		try:
			f_w.write(clevercss.convert(f_r.read()))
		finally:
			f_r.close()
			f_w.close()
	else:
		copyfile(settings.cssfile)
	basedir_files.remove(settings.cssfile)
	if settings.templatefile not in basedir_files:
		print("Template file not found!")
		return crash()
	f=open(os.path.join(settings.sourcedir, settings.templatefile))
	template = f.read()
	f.close()
	basedir_files.remove(settings.templatefile)
	if settings.homepagefile not in basedir_files:
		print("Home page file not found!")
		return crash()
	basedir_files.remove(settings.homepagefile)
	if settings.sensibleignore:
		basedir_files = [x for x in basedir_files if not (x.startswith('.') or x.endswith('~'))]
	for ignoreitem in settings.ignore:
		if ignoreitem in basedir_files:
			basedir_files.remove(ignoreitem)
	log('Files to process in base dir:')
	log('   '.join(basedir_files))
	wrongfiles = processtree('', basedir_files)
	log("Copying home page")
	tmp = open(os.path.join(settings.sourcedir, settings.homepagefile)).read()
	def repl(match):
		s = []
		for file in wrongfiles:
			s.append(match.group(1).format(**file))
		return '\n'.join(s)
	tmp = eachre.sub(repl, tmp)
	with open(os.path.join(settings.publishpath, 'index.html'), 'w') as f:
		f.write(tmp)

if __name__ == "__main__":
	main()
