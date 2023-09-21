from fpdf import FPDF
from fpdf.enums import XPos, YPos
from memory_profiler import profile


class Logger(object):

    """
    SINGLETON CLASS CONFIGURATION
    Logger Class calls on top of PDF Class which acts as an abstract class to allow subsequent declaration of Logger classes to work on
    """
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Logger, cls).__new__(cls)
            cls.pdf = PDF()
            cls.pdf.alias_nb_pages()
            cls.pdf.set_auto_page_break(auto=True, margin=4.0)
            cls.pdf.add_page(orientation='P', format='A4', same=False)
        return cls.instance

    def get_report(self):
        """
        Returns itself (PDF) object.

        Arguments:
        self  – local

        """
        return self.pdf

    #@profile()
    def write_report(self, content_type='text', content=""):
        """
        Returns void.
        It helps to write content from the system and device classes so that information is logged and subscribed to.

        Arguments:
        self  – local
        content_type - name

        """
        match content_type:
            case 'text':
                self.pdf.set_font(size=10)
                return self.pdf.cell(w=0, h=10, txt=str(content), border=0, align='L', fill=False, center=False, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            case 'chapter_title':
                # Set color
                self.pdf.set_draw_color(0, 80, 180)
                self.pdf.set_fill_color(230, 230, 0)

                # Set font size
                self.pdf.set_font(style='B', size=13)
                return self.pdf.cell(w=0, h=10, txt=str(content), border=0, align='C', fill=True, center=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            case 'page_break':
                self.pdf.add_page()

    def generate_report(self):
        return self.pdf.output('reports/surveillance.pdf', 'F')


class PDF(FPDF):

    def __init__(self):
        super().__init__()
        self.col = 0  # Current column
        self.y0 = 0  # Ordinate of column start

    def header(self):
        # Logo
        self.image('reports/logo/S.M.A.R.T.png', 10, 5, 35)
        # Arial bold 15
        self.set_font('Arial', 'B', 10)
        # Set cell text color
        self.set_text_color(220, 220, 220)
        # Move to the right
        self.cell(150, 0, "", 0)
        # Title
        self.cell(40, 30, 'Surveillance Report', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Line break
        self.ln(15)

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
