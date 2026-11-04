package cn.starcluster.controller;
import java.nio.file.*;
public class FpgaWireTest {
 public static void main(String[] args)throws Exception{
  byte[] expected=Files.readAllBytes(Paths.get(args[0]));
  byte[] actual=FpgaWire.frame(0,6,3,64,99,0,0xf1234567L,0x12345678L,0);
  if(!java.util.Arrays.equals(expected,actual))throw new AssertionError("Python wire reference mismatch");
  if(!FpgaWire.valid(actual))throw new AssertionError("valid frame rejected");
  for(int i=0;i<34;i++){byte[] broken=actual.clone();broken[i]^=1;if(FpgaWire.valid(broken))throw new AssertionError("corrupt byte "+i);}
  if(FpgaWire.u32(actual,10)!=0xf1234567L)throw new AssertionError("unsigned epoch");
  System.out.println("PASS: exact Python Event frame, 34 corrupt-byte rejection cases, unsigned epoch");
 }
}
