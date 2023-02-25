with Text_IO; use Text_IO;

procedure Hello is
    A : Integer := 12;
    B, C : Integer := 15;
begin
    A := B + C;
    Put_Line (A'Image);
end Hello;