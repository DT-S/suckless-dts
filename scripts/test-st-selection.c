/* Core scrollback/selection regressions; intentionally no X server needed.
 * Build: cc -std=c99 -D_XOPEN_SOURCE=600 -ffunction-sections -fdata-sections \
 *   scripts/test-st-selection.c -Wl,--gc-sections -o /tmp/test-st-selection
 */
#include <assert.h>
#include <locale.h>
#include "../st/st.c"

char *utmp, *scroll, *stty_args, *termname = "st-256color", *vtiden = "";
wchar_t *worddelimiters = L" ";
int allowaltscreen = 1, allowwindowops = 0;
unsigned int tabspaces = 8, defaultfg = 7, defaultbg = 0, defaultcs = 7;

/* Terminal parser callbacks: the tests inspect the terminal model directly. */
void xbell(void) {}
void xclipcopy(void) {}
void xdrawcursor(int x, int y, Glyph g, int ox, int oy, Glyph og) {}
void xdrawline(Line l, int a, int y, int b) {}
void xfinishdraw(void) {}
void xloadcols(void) {}
int xsetcolorname(int n, const char *s) { return 0; }
int xgetcolor(int n, unsigned char *r, unsigned char *g, unsigned char *b) { return 1; }
void xseticontitle(char *s) {}
void xsettitle(char *s) {}
int xsetcursor(int n) { return 0; }
void xsetmode(int set, unsigned int flags) {}
void xsetpointermotion(int set) {}
void xsetsel(char *s) { free(s); }
int xstartdraw(void) { return 0; }
void xximspot(int x, int y) {}

static int checks;

static void
expect(int condition, const char *name)
{
	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", name);
		exit(1);
	}
	checks++;
}

static void
expect_selection(const char *expected, const char *name)
{
	char *actual = getsel();
	if (!actual || strcmp(actual, expected)) {
		fprintf(stderr, "FAIL: %s\nexpected <%s>\nactual <%s>\n",
		        name, expected, actual ? actual : "NULL");
		exit(1);
	}
	free(actual);
	checks++;
}

static void
dispose(void)
{
	int i;

	for (i = 0; i < term.row; i++) {
		free(term.line[i]);
		free(term.alt[i]);
	}
	for (i = 0; i < HISTSIZE; i++)
		free(term.hist[i]);
	free(term.line);
	free(term.alt);
	free(term.tabs);
	free(term.dirty);
	term = (Term){0};
	selinit();
}

static void
reset_model(int col, int row)
{
	dispose();
	tnew(col, row);
}

static void
feed(const char *s)
{
	expect(twrite(s, strlen(s), 0) == (int)strlen(s), "parser consumed output");
}

static void
lines(int first, int last)
{
	char b[32];
	int i;

	for (i = first; i <= last; i++) {
		snprintf(b, sizeof b, "row-%03d\r\n", i);
		feed(b);
	}
}

static void
long_selection(void)
{
	char expected[512], line[32];
	int i;

	reset_model(16, 4);
	expect(scrollview(INT_MAX) == 0, "empty history has no phantom rows");
	lines(1, 20);
	expect(term.histlen == 17, "only real scrolled rows count");
	selstart(15, 2, 0);
	expect(selongoing(), "selection gesture started");
	expect(scrollview(10) == 10, "scroll ten rows");
	selextend(0, 0, SEL_REGULAR, 1);
	expect(!selongoing(), "release ends gesture");
	expected[0] = 0;
	for (i = 8; i <= 20; i++) {
		snprintf(line, sizeof line, "row-%03d\n", i);
		strcat(expected, line);
	}
	expect_selection(expected, "copy thirteen contiguous rows across viewport");
	expect(scrollview(INT_MAX) == 7, "clamp to valid oldest history");
	expect_selection(expected, "selection survives scrolling offscreen");
	expect(scrollview(INT_MIN) == -17, "clamp to live output without overflow");
	expect_selection(expected, "scrolling back preserves both endpoints");
}

static void
new_output(void)
{
	char *before;

	reset_model(16, 4);
	lines(1, 20);
	scrollview(10);
	selstart(0, 0, 0);
	selextend(6, 1, SEL_REGULAR, 0);
	before = getsel();
	lines(21, 24);
	expect(selongoing(), "new output does not cancel historic drag");
	expect_selection(before, "new output preserves selected text");
	expect(term.scr == 14, "view remains anchored while output arrives");
	free(before);
	selextend(6, 1, SEL_REGULAR, 1);
	before = getsel();
	tmoveto(0, 0);
	feed("LIVE");
	expect_selection(before, "live writes cannot clear same viewport row in history");
	free(before);
	scrollview(INT_MIN);
	selstart(0, 0, 0);
	selextend(3, 0, SEL_REGULAR, 1);
	tmoveto(0, 0);
	feed("X");
	expect(getsel() == NULL, "writing actual selected cells clears stale selection");
}

static void
visible_live_updates(void)
{
	reset_model(16, 4);
	lines(1, 10);
	scrollview(2);
	memset(term.dirty, 0, term.row * sizeof(*term.dirty));
	tmoveto(0, 0);
	feed("X");
	expect(term.dirty[2] && !term.dirty[0],
	       "live write repaints its displayed row while partially scrolled");
	memset(term.dirty, 0, term.row * sizeof(*term.dirty));
	tclearregion(0, 1, term.col - 1, 1);
	expect(term.dirty[3] && !term.dirty[1],
	       "live erase repaints its displayed row while partially scrolled");
}

static void
history_eviction(void)
{
	reset_model(16, 4);
	lines(1, HISTSIZE + 20);
	expect(term.histlen == HISTSIZE, "ring capacity bounded");
	scrollview(INT_MAX);
	selstart(0, 0, 0);
	selextend(6, 0, SEL_REGULAR, 1);
	expect_selection("row-018", "oldest retained row is chronological after ring wrap");
	lines(HISTSIZE + 21, HISTSIZE + 21);
	expect(getsel() == NULL, "selection cancels when its first row is evicted");
	expect(term.scr == HISTSIZE, "view remains bounded at saturated history");
}

static void
soft_wrap_and_unicode(void)
{
	reset_model(4, 3);
	feed("ab  cd");
	selstart(0, 0, 0);
	selextend(1, 1, SEL_REGULAR, 1);
	expect_selection("ab  cd", "soft wrap preserves internal spaces without newline");
	feed("\r\nx\r\ny\r\n");
	scrollview(INT_MAX);
	selstart(0, 0, 0);
	selextend(1, 1, SEL_REGULAR, 1);
	expect_selection("ab  cd", "soft wrap copied exactly from scrollback");

	reset_model(8, 3);
	feed("ä界Z");
	selstart(0, 0, 0);
	selextend(3, 0, SEL_REGULAR, 1);
	expect_selection("ä界Z", "UTF-8 and wide glyph dummy cell copied once");
}

static void
snap_and_rectangles(void)
{
	reset_model(4, 3);
	feed("abcdefghij\r\nx\r\ny\r\n");
	scrollview(2);
	selstart(1, 0, SNAP_WORD);
	selextend(1, 0, SEL_REGULAR, 1);
	expect_selection("abcdefghij", "word snap crosses invisible history boundary");
	selstart(1, 0, SNAP_LINE);
	selextend(1, 0, SEL_REGULAR, 1);
	expect_selection("abcdefghij\n", "line snap follows entire wrapped logical line");

	reset_model(8, 3);
	feed("   X\r\nabcdef");
	selstart(0, 0, 0);
	selextend(2, 1, SEL_RECTANGULAR, 1);
	expect_selection("\nabc", "blank rectangular segment has no out-of-bounds read");
	selstart(0, 0, 0);
	selextend(2, 0, SEL_REGULAR, 1);
	expect_selection("", "partial blank segment before nonblank text is safe");
}

static void
alternate_screen_and_regions(void)
{
	int histlen, histi;

	reset_model(16, 4);
	lines(1, 20);
	histlen = term.histlen;
	histi = term.histi;
	scrollview(3);
	selstart(0, 0, 0);
	feed("\033[?1049h");
	expect(tisaltscreen(), "alternate screen activated");
	expect(!selongoing() && getsel() == NULL, "screen switch cancels selection");
	lines(100, 130);
	expect(term.histlen == histlen && term.histi == histi,
	       "alternate output cannot contaminate normal history");
	expect(scrollview(20) == 0, "alternate screen cannot scroll normal history");
	feed("\033[?1049l");
	expect(!tisaltscreen(), "normal screen restored");
	expect(scrollview(3) == 3, "normal history available after alternate app");
	selstart(0, 0, 0);
	selextend(6, 0, SEL_REGULAR, 1);
	expect_selection("row-015", "normal history unchanged by alternate app");

	tsetscroll(1, 2);
	tscrollup(1, 1, 1);
	expect(term.histlen == histlen && term.histi == histi,
	       "partial scrolling region does not enter history");
	expect_selection("row-015", "partial live region does not clear historical selection");
	tscrolldown(1, 1);
	expect(term.histlen == histlen && term.histi == histi,
	       "reverse index does not reverse history ring");
}

static void
resize_and_small_terminal(void)
{
	reset_model(8, 3);
	lines(1, 10);
	scrollview(2);
	selstart(0, 0, 0);
	selextend(3, 1, SEL_REGULAR, 0);
	tresize(4, 2);
	expect(!selongoing() && getsel() == NULL, "resize safely cancels active selection");
	expect(scrollview(INT_MAX) > 0, "history still accessible after resize");
	selstart(0, 0, 0);
	selextend(3, 1, SEL_REGULAR, 1);
	free(getsel());
	tresize(32, 6);
	scrollview(INT_MAX);
	selstart(0, 0, 0);
	selextend(31, 5, SEL_REGULAR, 1);
	free(getsel());

	reset_model(8, 1);
	feed("a\r\nb\r\n");
	kscrollup(&(Arg){.i = -1});
	expect(term.scr == 1, "page up makes progress in one-row terminal");
	kscrolldown(&(Arg){.i = -1});
	expect(term.scr == 0, "page down makes progress in one-row terminal");
}

int
main(void)
{
	expect(setlocale(LC_CTYPE, "C.UTF-8") != NULL, "UTF-8 locale available");
	long_selection();
	new_output();
	visible_live_updates();
	history_eviction();
	soft_wrap_and_unicode();
	snap_and_rectangles();
	alternate_screen_and_regions();
	resize_and_small_terminal();
	dispose();
	free(strescseq.buf);
	printf("PASS: st scrollback selection (%d assertions)\n", checks);
	return 0;
}
