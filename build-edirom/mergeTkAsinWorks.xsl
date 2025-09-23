<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:mei="http://www.music-encoding.org/ns/mei" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="2.0">
  
  <xsl:output indent="yes"/>
  
  <xsl:param name="annots" select="document('./tmp/annots.xml')"/>
  <xsl:param name="properties" select="document('../../properties.xml')" />
  
  <xsl:template match="*">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$properties//property[@name='workTitle']"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:editionStmt/mei:edition">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$properties//property[@name='editionTitle']"/>
    </xsl:copy>

  </xsl:template>
  
  <xsl:template match="//mei:work/mei:notesStmt/*">
    <xsl:copy-of select="$annots"/>
  </xsl:template>
</xsl:stylesheet>