#!/usr/bin/env python
# coding=UTF-8

# Based on code by Toni Cebrián: 
# http://www.tonicebrian.com/posts/2010/10/15/continuous-integration-for-c-using-hudson.html

import xml.etree.ElementTree as ET
import getopt, os, re, sys

# The default number of tests to publish. Using a fixed number allows tracking
# progress over time in Hudson/Jenkins. This however does not apply for
# TeamCity. The value of 0 means, that no fake passed tests are added to reach
# a fixed number.
DEFAULT_TEST_COUNT = 0

def shorten_path(path):
    return re.sub(os.getcwd() + '/', '', path)

def transform(infile = sys.stdin, outfile = sys.stdout, test_count = DEFAULT_TEST_COUNT):
    if infile == '-':
        infile = sys.stdin

    if type(outfile) == file:
        out = outfile
    else:
        out = open(outfile, 'w')

    doc = ET.parse(infile)
    exe = os.path.abspath(doc.findtext('args/argv/exe'))
    errors = doc.findall('.//error')
    error_count = len(errors)

    out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    # In xUnit, the errors from the valgrind XML output become "failures".
    # Failures are tests that failed (an equivalent of a yellow ball in
    # Hudson/Jenkins), while errors are test runs that did not complete
    # successfully for other reasons (an equivalent of a red ball in
    # Hudson/Jenkins).
    out.write('<testsuite name="{0} memcheck" tests="{1}" errors="0" failures="{2}" skip="0">\n'.format(shorten_path(exe), test_count or error_count, error_count))
    i = 0
    for error in errors:
        i = i + 1
        kind = error.findtext('kind')
        message = error.findtext('xwhat/text', '') or error.findtext('what', '')
        out.write('    <testcase classname="ValgrindMemoryCheck" name="Memory check #{0:04d}" time="0">\n'.format(i))
        out.write('        <failure type="{0}" message="{1}">\n'.format(kind, message.strip()))
        out.write('            <![CDATA[\n')
        frames = error.findall('stack/frame')
        # Present a stack trace in a human-friendly way.
        for frame in frames:
            out.write('            {0} {1}\n'.format(frame.findtext('ip', '?????????'), frame.findtext('fn', '??')))
            if frame.find('file') is not None:
                out.write('                in {0}/{1}:{2}\n'.format(shorten_path(frame.findtext('dir')), frame.findtext('file'), frame.findtext('line')))
            elif frame.find('obj') is not None:
                out.write('                in {0}\n'.format(shorten_path(frame.findtext('obj'))))
        out.write('            ]]>\n')
        out.write('        </failure>\n')
        out.write('    </testcase>\n')
    # Add the fake passed tests, so we have test_count tests total.
    for j in range(test_count - error_count):
        i = i + 1
        out.write('    <testcase classname="ValgrindMemoryCheck" name="Memory check #{0:04d}" time="0"></testcase>\n'.format(i))
    out.write('</testsuite>\n')
    out.close()

def main():
    script_name = os.path.basename(sys.argv[0])
    output = sys.stdout
    test_count = DEFAULT_TEST_COUNT

    def help():
        print("USAGE: {0} [options] <infile>".format(script_name))
        print('Transform valgrind XML to xUnit format.')
        print("  -h | --help\t\tprint this help and exit")
        print("  -o | --output\t\tset the output file name [stdout]")
        print("  -t | --test-count\tset the number of tests to publish [{0}]".format(test_count or ''))
        sys.exit(2)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ho:t:', ['help', 'output=', 'test-count='])
    except getopt.GetoptError as err:
        sys.stderr.write("{0}: {1}\nTry `{0} --help' for more information.\n".format(script_name, err))
        sys.exit(2)
    
    for o, a in opts:
        if o in ('-o', '--output'):
            output = a
        elif o in ('-t', '--test-count'):
            test_count = int(a)
        else: # o in ("-h", "--help"):
            help()

    if len(args) == 1:
        transform(args[0], output, test_count)
    else:
        help()

# Don't run main() if the script is used as a library.
if __name__ == "__main__":
    main()
